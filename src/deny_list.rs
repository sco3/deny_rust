use aho_corasick::AhoCorasick;
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3::pyclass;
use pyo3::types::{PyDict, PyDictMethods};

#[pyclass(from_py_object)]
#[derive(Clone)]
pub struct DenyList {
    pub ac: AhoCorasick,
}

#[pymethods]
impl DenyList {
    #[new]
    fn new(words: Vec<String>) -> PyResult<Self> {
        let ac = AhoCorasick::new(words)
            .map_err(|e| PyValueError::new_err(format!("Invalid patterns: {}", e)))?;
        Ok(Self { ac })
    }

    /// scans dict and returns true if match found
    pub fn scan(&self, args: &Bound<'_, PyDict>) -> bool {
        for value in args.values() {
            if let Ok(value_str) = value.extract::<&str>() {
                if self.ac.is_match(value_str) {
                    return true;
                }
            }
        }
        false
    }

    /// scans str and returns true if match found
    pub fn scan_str(&self, txt: &str) -> bool {
        if self.ac.is_match(txt) {
            return true;
        }
        false
    }
}
