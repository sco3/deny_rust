use pyo3::{Bound, PyAny, PyResult};
use pyo3::types::PyDict;

/// A trait for types that can match string against provided patterns
pub trait Matcher {
    /// Check if the given string matches according to the implementing type's logic
    fn is_match(&self, s: &str) -> bool;
    fn scan(&self, args: &Bound<'_, PyDict>) -> bool;
    fn scan_str(&self, txt: &str) -> bool;
    fn scan_any(&self, value: &Bound<'_, PyAny>) -> PyResult<bool>;
}
