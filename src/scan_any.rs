use crate::matcher::Matcher;
use pyo3::prelude::PyAnyMethods;
use pyo3::types::PyDictMethods;
use pyo3::types::{PyDict, PyList};
use pyo3::{Bound, PyAny, PyResult};

pub(crate) fn scan_any<M: Matcher>(matcher: &M, value: &Bound<'_, PyAny>) -> PyResult<bool> {
    // 1. Check for String
    if let Ok(s) = value.extract::<&str>() {
        if matcher.is_match(s) {
            return Ok(true);
        }
    }
    // 2. Check for Dictionary
    else if let Ok(dict) = value.cast::<PyDict>() {
        // In the Bound API, downcast returns &Bound<PyDict>
        for item_value in dict.values() {
            if scan_any(matcher, &item_value)? {
                return Ok(true);
            }
        }
    }
    // 3. Check for List
    else if let Ok(list) = value.cast::<PyList>() {
        for item in list {
            if scan_any(matcher, &item)? {
                return Ok(true);
            }
        }
    }

    Ok(false)
}

/// scans single level dictionary
pub(crate) fn scan<M:Matcher>(matcher: &M, args: &Bound<'_, PyDict>) -> bool {
    for value in args.values() {
        if let Ok(value_str) = value.extract::<&str>() {
            if matcher.is_match(value_str) {
                return true;
            }
        }
    }
    false
}