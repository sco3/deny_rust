use crate::deny_list_config::DenyListConfig;
use aho_corasick::AhoCorasick;
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3::pyclass;
use pyo3::types::{PyDict, PyDictMethods};

#[pyclass]
pub struct PluginViolation {
    #[pyo3(get, set)]
    pub reason: String,
    #[pyo3(get, set)]
    pub description: String,
    #[pyo3(get, set)]
    pub code: String,
    #[pyo3(get, set)]
    pub details: Option<Py<PyDict>>,
    #[pyo3(get, set)]
    pub plugin_name: String,
    #[pyo3(get, set)]
    pub mcp_error_code: Option<i32>,
}

#[pymethods]
impl PluginViolation {
    #[new]
    #[pyo3(signature = (reason, description, code, details=None, plugin_name=String::from(""), mcp_error_code=None))]
    fn new(
        reason: String,
        description: String,
        code: String,
        details: Option<Py<PyDict>>,
        plugin_name: String,
        mcp_error_code: Option<i32>,
    ) -> Self {
        Self {
            reason,
            description,
            code,
            details,
            plugin_name,
            mcp_error_code,
        }
    }
}

#[pyclass]
pub struct PluginResult {
    #[pyo3(get, set)]
    pub continue_processing: bool,
    #[pyo3(get, set)]
    pub modified_payload: Option<Py<PyDict>>,
    #[pyo3(get, set)]
    pub violation: Option<Py<PluginViolation>>,
    #[pyo3(get, set)]
    pub metadata: Option<Py<PyDict>>,
}

#[pymethods]
impl PluginResult {
    #[new]
    #[pyo3(signature = (continue_processing=true, modified_payload=None, violation=None, metadata=None))]
    fn new(
        continue_processing: bool,
        modified_payload: Option<Py<PyDict>>,
        violation: Option<Py<PluginViolation>>,
        metadata: Option<Py<PyDict>>,
    ) -> Self {
        Self {
            continue_processing,
            modified_payload,
            violation,
            metadata,
        }
    }
}

#[pyclass(from_py_object)]
#[derive(Clone)]
pub struct DenyListPlugin {
    pub ac: AhoCorasick,
    pub plugin_name: String,
}

#[pymethods]
impl DenyListPlugin {
    #[new]
    #[pyo3(signature = (config, plugin_name=String::from("DenyListPlugin")))]
    fn new(config: DenyListConfig, plugin_name: String) -> PyResult<Self> {
        let ac = AhoCorasick::new(config.words)
            .map_err(|e| PyValueError::new_err(format!("Invalid patterns: {}", e)))?;
        Ok(Self { ac, plugin_name })
    }

    fn prompt_pre_fetch(&self, args: &Bound<'_, PyDict>) -> PyResult<Py<PluginResult>> {
        let py = args.py();
        
        for value in args.values() {
            let value_str = value.extract::<&str>()?;

            if self.ac.is_match(value_str) {
                // Create violation
                let violation = Py::new(
                    py,
                    PluginViolation {
                        reason: "Denied word found in prompt".to_string(),
                        description: "The prompt contains words from the deny list".to_string(),
                        code: "DENY_LIST_VIOLATION".to_string(),
                        details: None,
                        plugin_name: self.plugin_name.clone(),
                        mcp_error_code: None,
                    },
                )?;

                // Create result with violation
                let result = Py::new(
                    py,
                    PluginResult {
                        continue_processing: false,
                        modified_payload: None,
                        violation: Some(violation),
                        metadata: None,
                    },
                )?;

                return Ok(result);
            }
        }

        // No violation found - continue processing
        let result = Py::new(
            py,
            PluginResult {
                continue_processing: true,
                modified_payload: None,
                violation: None,
                metadata: None,
            },
        )?;

        Ok(result)
    }

    // Keep the old scan method for backward compatibility
    pub fn scan(&self, args: &Bound<'_, PyDict>) -> PyResult<bool> {
        for value in args.values() {
            let value_str = value.extract::<&str>()?;

            if self.ac.is_match(value_str) {
                return Ok(false);
            }
        }
        Ok(true)
    }
}
