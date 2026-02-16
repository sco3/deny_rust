use crate::matcher::Matcher;
use crate::scan_any;
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

    /// scans single level dictionary like in existing plugion
    fn scan(&self, args: &Bound<'_, PyDict>) -> bool {
        scan_any::scan(self, args)
    }

    ///scans string and gives true on found denied words
    fn scan_str(&self, txt: &str) -> bool {
        self.rs.is_match(txt)
    }

    /// scans str,dict,list and returns true if match found
    fn scan_any(&self, value: &Bound<'_, PyAny>) -> PyResult<bool> {
        scan_any::scan_any(self, value)
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

}
