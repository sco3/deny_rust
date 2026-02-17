use crate::build_error::build_error;
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
    /// constructor
    /// # Errors
    /// * regex problems (should not happen with simple match)
    #[new]
    pub fn new(words: Vec<String>) -> PyResult<Self> {
        let patterns: Vec<String> = words.into_iter().map(|w| escape(&w)).collect();

        let rs = RegexSet::new(patterns).map_err(build_error)?;

        Ok(Self { rs })
    }
    /// check string for deny word
    #[must_use]
    pub fn is_match(&self, s: &str) -> bool {
        Matcher::is_match(self, s)
    }
    /// scans one level of dict
    #[must_use]
    pub fn scan(&self, args: &Bound<'_, PyDict>) -> bool {
        Matcher::scan(self, args)
    }
    /// scans dict,str,list
    #[must_use]
    pub fn scan_any(&self, value: &Bound<'_, PyAny>) -> bool {
        Matcher::scan_any(self, value)
    }
    /// scans dict,str,list from msg pack
    #[must_use]
    pub fn scan_msgpack(&self, value: &[u8]) -> bool {
        Matcher::scan_msgpack(self, value)
    }
}
