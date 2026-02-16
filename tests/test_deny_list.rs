use deny_rust::deny_list::DenyList;
use deny_rust::deny_list_rs::DenyListRs;

use deny_rust::module::deny_rust as dr;
use pyo3::PyResult;
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};

const DENY_WORDS: &[&str] = &["asdf", "jkl"];
const BLOCK_PROMPT: &str = "111  asdf 222";
const OK_PROMPT: &str = "111 222 333";

fn common_test_logic<T: deny_rust::matcher::Matcher>(deny_list: T, py: Python) {
    assert!(deny_list.is_match("111  asdf  222"));
    assert!(deny_list.is_match("111  asdf  222 jkl"));
    assert!(!deny_list.is_match("111 222"));
    let dict = PyDict::new(py);
    let list_data: Vec<String> = BLOCK_PROMPT.split(' ').map(|s| s.to_string()).collect();
    let list = PyList::new(py, list_data).unwrap();

    dict.set_item("user", BLOCK_PROMPT).unwrap();
    assert!(deny_list.scan_str(BLOCK_PROMPT));
    assert!(deny_list.scan(&dict));
    assert!(deny_list.scan_any(&dict).unwrap());
    assert!(deny_list.scan_any(&list).unwrap());

    dict.clear();
    let list_data: Vec<String> = OK_PROMPT.split(' ').map(|s| s.to_string()).collect();
    let list = PyList::new(py, &list_data).unwrap();
    dict.set_item("user", OK_PROMPT).unwrap();
    assert!(!deny_list.scan_str(OK_PROMPT));
    assert!(!deny_list.scan(&dict));
    assert!(!deny_list.scan_any(&dict).unwrap());
    assert!(!deny_list.scan_any(&list).unwrap());
}

#[test]
fn test_deny_lists() -> PyResult<()> {
    let words: Vec<String> = DENY_WORDS.iter().map(|s| s.to_string()).collect();
    let deny_list = DenyList::new(words.clone())?;
    let deny_list_rs = DenyListRs::new(words)?;

    Python::initialize();
    Python::attach(|py| {
        common_test_logic(deny_list, py);
        common_test_logic(deny_list_rs, py);
        let module = PyModule::new(py, "modules").unwrap();
        dr(&module).unwrap();
    });

    Ok(())
}
