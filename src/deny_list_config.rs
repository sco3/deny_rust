use pyo3::{pyclass, pymethods};

#[pyclass(from_py_object, module = "deny_rust")]
#[derive(Clone)]
pub struct DenyListConfig {
    pub words: Vec<String>,
}

#[pymethods]
impl DenyListConfig {
    #[new]
    // This allows you to call DenyListConfig(words=[...]) in Python
    pub fn new(words: Vec<String>) -> Self {
        DenyListConfig { words }
    }
}
