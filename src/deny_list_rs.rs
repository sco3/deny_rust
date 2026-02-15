use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};
use regex::{escape, RegexSet};

#[pyclass(from_py_object)]
#[derive(Clone)]
pub struct DenyListRs {
    rs: RegexSet,
}

#[pymethods]
impl DenyListRs {
    #[new]
    fn new(words: Vec<String>) -> PyResult<Self> {
        let patterns: Vec<String> = words.into_iter().map(|w| escape(&w)).collect();

        let rs = RegexSet::new(patterns)
            .map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))?;

        Ok(Self { rs })
    }

    pub fn scan_str(&self, txt: &str) -> bool {
        self.rs.is_match(txt)
    }

    /// scans str,dict,list and returns true if match found
    fn scan_any(&self, value: &Bound<'_, PyAny>) -> PyResult<bool> {
        // 1. Check for String
        if let Ok(s) = value.extract::<&str>() {
            if self.rs.is_match(s) {
                return Ok(true);
            }
        }
        // 2. Check for Dictionary
        else if let Ok(dict) = value.cast::<PyDict>() {
            // In the Bound API, downcast returns &Bound<PyDict>
            for item_value in dict.values() {
                if self.scan_any(&item_value)? {
                    return Ok(true);
                }
            }
        }
        // 3. Check for List
        else if let Ok(list) = value.cast::<PyList>() {
            for item in list {
                if self.scan_any(&item)? {
                    return Ok(true);
                }
            }
        }

        Ok(false)
    }
    pub fn scan(&self, args: &Bound<'_, PyDict>) -> bool {
        self.scan_any(args.as_any()).unwrap_or(false)
    }
}
