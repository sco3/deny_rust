use crate::build_error::build_error;
use crate::matcher::Matcher;
use daachorse::DoubleArrayAhoCorasick as Daac;
use daachorse::DoubleArrayAhoCorasickBuilder as DaacBld;
use daachorse::MatchKind::LeftmostFirst;
use pyo3::prelude::*;
use pyo3::pyclass;
use pyo3::types::PyDict;
use pyo3_stub_gen::derive::{gen_stub_pyclass, gen_stub_pymethods};

#[gen_stub_pyclass]
#[pyclass(skip_from_py_object)]
pub struct DenyListDaac {
    pub daac: Daac<usize>,
}

impl Matcher for DenyListDaac {
    /// Performs a case-insensitive leftmost-first pattern match against the automaton.
    ///
    /// This method lowercases the input and returns whether any pattern in the
    /// underlying DAAC matches as the leftmost match.
    ///
    /// # Examples
    ///
    /// ```
    /// // Construct a matcher that flags the word "bad" and test matching.
    /// let matcher = DenyListDaac::new(vec!["bad".to_string()]).unwrap();
    /// assert!(matcher.is_match("This is BAD"));
    /// assert!(!matcher.is_match("All good"));
    /// ```
    fn is_match(&self, s: &str) -> bool {
        // Convert input to lowercase for case-insensitive matching
        //self.daac.find_iter(&s.to_lowercase()).next().is_some()
        self.daac
            .leftmost_find_iter(&s.to_lowercase())
            .next()
            .is_some()
    }
}

#[gen_stub_pymethods]
#[pymethods]
impl DenyListDaac {
    /// Creates a new DenyListDaac from the provided word list.
    ///
    /// The provided words are converted to lowercase and used to build a
    /// Double-Array Aho–Corasick automaton with leftmost-first matching,
    /// enabling case-insensitive matching against input text.
    ///
    /// # Errors
    ///
    /// Returns a PyErr when the underlying DAAC builder fails (for example,
    /// if a pattern is too long or other daachorse build constraints are violated).
    ///
    /// # Examples
    ///
    /// ```
    /// use your_crate::DenyListDaac;
    ///
    /// let deny = DenyListDaac::new(vec!["Bad".to_string(), "Evil".to_string()]).unwrap();
    /// assert!(deny.is_match("this is bad"));
    /// assert!(deny.is_match("an EVIL deed"));
    /// ```
    #[new]
    pub fn new(words: Vec<String>) -> PyResult<Self> {
        // Store deny words in lowercase for case-insensitive matching
        let words_lower: Vec<String> = words.into_iter().map(|w| w.to_lowercase()).collect();

        let daac = DaacBld::new()
            .match_kind(LeftmostFirst)
            .build(&words_lower)
            .map_err(build_error)?;

        Ok(Self { daac })
    }

    /// Checks whether the input contains any denylist pattern (case-insensitive).
    ///
    /// This performs a case-insensitive search of `s` against the matcher's patterns and
    /// returns whether at least one pattern is found.
    ///
    /// # Examples
    ///
    /// ```
    /// // Build a deny list with one pattern and test matching.
    /// let dl = crate::deny_list_daac::DenyListDaac::new(vec!["bad".to_string()]).unwrap();
    /// assert!(dl.is_match("This is bad"));
    /// assert!(!dl.is_match("This is fine"));
    /// ```
    #[must_use]
    pub fn is_match(&self, s: &str) -> bool {
        Matcher::is_match(self, s)
    }
    /// Scan a string for any deny-list pattern using this matcher.
    ///
    /// # Returns
    ///
    /// `true` if a deny-list pattern is found, `false` otherwise.
    ///
    /// # Examples
    ///
    /// ```
    /// # use crate::deny_list_daac::DenyListDaac;
    /// let m = DenyListDaac::new(vec!["bad".into()]).unwrap();
    /// assert!(m.scan_str("this is bad"));
    /// assert!(!m.scan_str("this is fine"));
    /// ```
    pub fn scan_str(&self, txt: &str) -> bool {
        Matcher::scan_str(self, txt)
    }
    /// Scan a Python dictionary for any deny-list matches.
    ///
    /// # Parameters
    ///
    /// * `args` - A bound reference to a Python `dict` containing the values to inspect. The function examines strings inside the dictionary for deny-list entries.
    ///
    /// # Returns
    ///
    /// `true` if any deny-list entry matches data found in `args`, `false` otherwise.
    ///
    /// # Examples
    ///
    /// ```no_run
    /// use pyo3::prelude::*;
    /// use pyo3::types::PyDict;
    ///
    /// // Acquire the GIL and build a sample args dict.
    /// let gil = Python::acquire_gil();
    /// let py = gil.python();
    /// let args = PyDict::new(py);
    /// args.set_item("text", "Example content with BADWORD").unwrap();
    ///
    /// // Construct a deny list and scan the args dict.
    /// let deny = DenyListDaac::new(vec!["badword".to_string()]).unwrap();
    /// assert!(deny.scan(&args));
    /// ```
    pub fn scan(&self, args: &Bound<'_, PyDict>) -> bool {
        Matcher::scan(self, args)
    }
    /// Scans a Python object (string, sequence, mapping, or nested combination) for any denylist match.
    ///
    /// The scan inspects string values found anywhere inside the provided Python object and performs a case-insensitive match against the denylist.
    ///
    /// # Parameters
    ///
    /// * `value` - Python object to scan; may be a scalar, sequence, mapping, or nested combination.
    ///
    /// # Returns
    ///
    /// `true` if a denylist match was found anywhere within `value`, `false` otherwise.
    ///
    /// # Examples
    ///
    /// ```
    /// use pyo3::prelude::*;
    /// let matcher = DenyListDaac::new(vec!["bad".into()]).unwrap();
    /// Python::with_gil(|py| {
    ///     let v = "this is bad".to_object(py);
    ///     assert!(matcher.scan_any(&v.as_ref(py)));
    /// });
    /// ```
    #[must_use]
    pub fn scan_any(&self, value: &Bound<'_, PyAny>) -> bool {
        Matcher::scan_any(self, value)
    }
}