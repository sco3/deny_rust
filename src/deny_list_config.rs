use pyo3::pyclass;

#[pyclass(from_py_object)]
#[derive(Clone)]
pub struct DenyListConfig {
    pub words: Vec<String>,
}
