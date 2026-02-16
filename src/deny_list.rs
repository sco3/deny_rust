use aho_corasick::{AhoCorasick, BuildError, MatchKind};
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;

use crate::matcher::Matcher;
use crate::scan_any;
use pyo3::pyclass;
use pyo3::types::PyDict;

#[pyclass(from_py_object)]
#[derive(Clone)]
pub struct DenyList {
    pub ac: AhoCorasick,
}

fn error_words() -> fn(BuildError) -> PyErr {
    |e| PyValueError::new_err(format!("Invalid patterns: {}", e))
}

impl Matcher for DenyList {
    /// implements match with aho-corasic
    fn is_match(&self, s: &str) -> bool {
        self.ac.is_match(s)
    }

    fn scan(&self, args: &Bound<'_, PyDict>) -> bool {
        scan_any::scan(self, args)
    }

    /// scans str and returns true if match found
    fn scan_str(&self, txt: &str) -> bool {
        self.ac.is_match(txt)
    }

    /// scans str,dict,list and returns true if match found
    fn scan_any(&self, value: &Bound<'_, PyAny>) -> PyResult<bool> {
        scan_any::scan_any(self, value)
    }
}

#[pymethods]
impl DenyList {
    #[new]
    pub fn new(words: Vec<String>) -> PyResult<Self> {
        let ac = AhoCorasick::builder()
            .match_kind(MatchKind::LeftmostFirst)
            .build(words)
            .map_err(error_words())?;

        Ok(Self { ac })
    }
}
