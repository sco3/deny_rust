pub use crate::deny_list::DenyList;
pub use crate::deny_list_rs::DenyListRs;
use pyo3_stub_gen::define_stub_info_gatherer;

use crate::deny_list_daac::DenyListDaac;
use pyo3::prelude::*;

/// Register deny-list types into the given Python module.
///
/// Adds the Rust-backed Python classes `DenyList`, `DenyListRs`, and `DenyListDaac` to the provided module.
///
/// # Errors
///
/// Returns a `PyErr` if registration of any of the classes into the module fails.
///
/// # Examples
///
/// ```
/// use pyo3::prelude::*;
/// use pyo3::types::PyModule;
///
/// let gil = Python::acquire_gil();
/// let py = gil.python();
/// let m = PyModule::new(py, "test").unwrap();
/// // `deny_filter` registers the classes on `m`; it returns `Ok(())` on success.
/// deny_filter(m).unwrap();
/// ```
#[pymodule]
pub fn deny_filter(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<DenyList>()?;
    m.add_class::<DenyListRs>()?;
    m.add_class::<DenyListDaac>()?;
    Ok(())
}

define_stub_info_gatherer!(stub_info);