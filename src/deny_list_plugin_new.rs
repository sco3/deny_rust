use pyo3::pymethods;
use crate::deny_list_config::DenyListConfig;
use crate::deny_list_plugin::DenyListPlugin;

#[pymethods]
impl DenyListPlugin {
    #[new]
    fn new(config: DenyListConfig) -> Self {
        Self { deny_words: config.words }
    }
}
