use pyo3::prelude::*;
use pyo3::types::PyDict;
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

    pub fn scan(&self, args: &Bound<'_, PyDict>) -> bool {
        for value in args.values() {
            if let Ok(s) = value.extract::<&str>() {
                if self.rs.is_match(s) {
                    return true;
                }
            }
        }
        false
    }
}
