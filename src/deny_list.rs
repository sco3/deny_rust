use aho_corasick::{AhoCorasick, BuildError, MatchKind};
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;

use crate::matcher::Matcher;
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
    fn is_match(&self, s: &str) -> bool {
        Matcher::is_match(self, s)
    }
    fn scan_str(&self, txt: &str) -> bool {
        Matcher::scan_str(self, txt)
    }
    fn scan(&self, args: &Bound<'_, PyDict>) -> bool {
        Matcher::scan(self, args)
    }
    fn scan_any(&self, value: &Bound<'_, PyAny>) -> PyResult<bool> {
        Matcher::scan_any(self, value)
    }
}
