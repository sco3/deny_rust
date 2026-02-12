use crate::deny_list_config::DenyListConfig;
use aho_corasick::AhoCorasick;
use pyo3::prelude::*;
use pyo3::pyclass;
use pyo3::types::{PyDict, PyDictMethods};

#[pyclass(from_py_object)]
#[derive(Clone)]
pub struct DenyListPlugin {
    pub ac: AhoCorasick,
}

#[pymethods]
impl DenyListPlugin {
    #[new]
    fn new(config: DenyListConfig) -> PyResult<Self> {
        let ac = AhoCorasick::new(config.words.into_iter())?;
        Ok(Self { ac })
    }

    pub fn scan(&self, args: &Bound<'_, PyDict>) -> PyResult<bool> {
        for value in args.values() {
            // Explicitly tell extract what type we want
            let value_str = value.extract::<&str>()?;

            if self.ac.is_match(value_str) {
                return Ok(false);
            }
        }
        Ok(true)
    }
}
