pub mod deny_list;

use crate::deny_list::DenyList;
use pyo3::prelude::*;

#[pymodule]
fn deny_rust(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<DenyList>()?;
    Ok(())
}
