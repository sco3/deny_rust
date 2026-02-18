pub use crate::deny_list::DenyList;
pub use crate::deny_list_rs::DenyListRs;

use pyo3::prelude::*;

#[pymodule]
/// python module compose
/// # Errors
/// * methods not found
pub fn deny_filter(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<DenyList>()?;
    m.add_class::<DenyListRs>()?;
    Ok(())
}
