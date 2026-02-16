pub mod deny_list;
pub mod deny_list_rs;
pub mod matcher;
pub mod scan_any;

pub use crate::deny_list::DenyList;
pub use crate::deny_list_rs::DenyListRs;

use pyo3::prelude::*;

#[pymodule]
fn deny_rust(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<DenyList>()?;
    m.add_class::<DenyListRs>()?;
    Ok(())
}
