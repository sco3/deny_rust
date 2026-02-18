pub mod build_error;
pub mod deny_list;
pub mod deny_list_rs;
pub mod matcher;
pub mod pymodule;

use pyo3_stub_gen::define_stub_info_gatherer;

define_stub_info_gatherer!(stub_info);
