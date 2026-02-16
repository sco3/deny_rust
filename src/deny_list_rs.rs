use crate::matcher::Matcher;
use pyo3::prelude::*;
use pyo3::types::PyDict;
use regex::{RegexSet, escape};

#[pyclass(from_py_object)]
#[derive(Clone)]
pub struct DenyListRs {
    rs: RegexSet,
}

impl Matcher for DenyListRs {
    /// implements matching with regex set
    fn is_match(&self, s: &str) -> bool {
        self.rs.is_match(s)
    }
}

#[pymethods]
impl DenyListRs {
    #[new]
    pub fn new(words: Vec<String>) -> PyResult<Self> {
        let patterns: Vec<String> = words.into_iter().map(|w| escape(&w)).collect();

        let rs = RegexSet::new(patterns)
            .map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))?;

        Ok(Self { rs })
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
