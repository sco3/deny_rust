use crate::build_error::build_error;
use crate::matcher::Matcher;
use daachorse::MatchKind;
use daachorse::charwise::CharwiseDoubleArrayAhoCorasick as Daac;
use daachorse::charwise::CharwiseDoubleArrayAhoCorasickBuilder as DaacBuilder;
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
    /// implements match with aho-corasic
    fn is_match(&self, s: &str) -> bool {
        // Convert input to lowercase for case-insensitive matching
        self.daac.find_iter(&s.to_lowercase()).next().is_some()
    }
}

#[gen_stub_pymethods]
#[pymethods]
impl DenyListDaac {
    /// constructor
    /// # Errors
    /// * aho-corasic errors (too long patterns)
    #[new]
    pub fn new(words: Vec<String>) -> PyResult<Self> {
        // Store deny words in lowercase for case-insensitive matching
        let words_lower: Vec<String> = words.into_iter().map(|w| w.to_lowercase()).collect();

        let daac = DaacBuilder::new()
            .match_kind(MatchKind::LeftmostFirst)
            .build(words_lower)
            .map_err(build_error)?;

        Ok(Self { daac })
    }

    #[must_use]
    pub fn is_match(&self, s: &str) -> bool {
        Matcher::is_match(self, s)
    }
    #[must_use]
    pub fn scan_str(&self, txt: &str) -> bool {
        Matcher::scan_str(self, txt)
    }
    #[must_use]
    pub fn scan(&self, args: &Bound<'_, PyDict>) -> bool {
        Matcher::scan(self, args)
    }
    /// scans dict,str,list
    #[must_use]
    pub fn scan_any(&self, value: &Bound<'_, PyAny>) -> bool {
        Matcher::scan_any(self, value)
    }
}
