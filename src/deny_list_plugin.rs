use pyo3::pyclass;

#[pyclass(from_py_object)]
#[derive(Clone)]
pub struct DenyListPlugin {
    pub deny_words: Vec<String>,
}
