pub mod deny_list_config;
pub mod deny_list_plugin;

use crate::deny_list_config::DenyListConfig;
use crate::deny_list_plugin::{DenyListPlugin, PluginResult, PluginViolation};
use pyo3::prelude::*;

#[pymodule]
fn deny_rust(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<DenyListPlugin>()?;
    m.add_class::<DenyListConfig>()?;
    m.add_class::<PluginResult>()?;
    m.add_class::<PluginViolation>()?;
    Ok(())
}