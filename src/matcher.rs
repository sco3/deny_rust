use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};
use rmp::Marker;
use rmp::decode::{read_array_len, read_map_len, read_marker, read_str_from_slice};
use std::io::Cursor;

pub trait Matcher {
    fn is_match(&self, s: &str) -> bool;

    /// Shared logic: Scans single level dictionary
    fn scan(&self, args: &Bound<'_, PyDict>) -> bool {
        for value in args.values() {
            if let Ok(value_str) = value.extract::<&str>()
                && self.is_match(value_str)
            {
                return true;
            }
        }
        false
    }

    /// Shared logic: The recursive engine for any Python object
    /// # Errors
    /// * too deep dictionaries, too long patterns probably
    fn scan_any(&self, value: &Bound<'_, PyAny>) -> bool {
        // 1. Check for String
        if let Ok(s) = value.extract::<&str>() {
            if self.is_match(s) {
                return true;
            }
        }
        // 2. Check for Dictionary
        else if let Ok(dict) = value.cast::<PyDict>() {
            for item_value in dict.values() {
                if self.scan_any(&item_value) {
                    return true;
                }
            }
        }
        // 3. Check for List
        else if let Ok(list) = value.cast::<PyList>() {
            for item in list {
                if self.scan_any(&item) {
                    return true;
                }
            }
        }
        false
    }
    /// Scans message pack structures for deny words
    fn scan_msgpack(&self, value: &[u8]) -> bool {
        let mut cur = Cursor::new(value);
        self.traverse(&mut cur, value, true)
    }

    /// Traverses msgpack bytes recursively, returns true if a violation is found
    fn traverse(&self, cur: &mut Cursor<&[u8]>, full_data: &[u8], check_strings: bool) -> bool {
        #[allow(clippy::cast_possible_truncation)]
        let pos = cur.position() as usize;

        if pos >= full_data.len() {
            return false;
        }

        let Ok(marker) = read_marker(cur) else {
            return false;
        };

        match marker {
            // str
            Marker::FixStr(_) | Marker::Str8 | Marker::Str16 | Marker::Str32 => {
                let data_slice = &full_data[pos..];
                if let Ok((found_str, tail)) = read_str_from_slice(data_slice) {
                    if check_strings {
                        //let type_name = std::any::type_name::<Self>();
                        //println!("check [{}]: {found_str}", type_name.split("::").last().unwrap_or(type_name));

                        if self.is_match(found_str) {
                            return true; // violation found
                        }
                    }
                    // Advance cursor by the number of bytes consumed
                    let bytes_consumed = data_slice.len() - tail.len();
                    cur.set_position((pos + bytes_consumed) as u64);
                }
            }

            // list
            Marker::FixArray(_) | Marker::Array16 | Marker::Array32 => {
                cur.set_position(pos as u64); // Reset to read length
                if let Ok(len) = read_array_len(cur) {
                    for _ in 0..len {
                        if self.traverse(cur, full_data, check_strings) {
                            return true;
                        }
                    }
                }
            }

            // map
            Marker::FixMap(_) | Marker::Map16 | Marker::Map32 => {
                cur.set_position(pos as u64);
                if let Ok(len) = read_map_len(cur) {
                    for _ in 0..len {
                        // Traverse key (don't check strings in keys)
                        if self.traverse(cur, full_data, false) {
                            return true;
                        }
                        // Traverse value (check strings in values)
                        if self.traverse(cur, full_data, check_strings) {
                            return true;
                        }
                    }
                }
            }
            _ => {} // other types (int, nil, bool, etc.) - skip
        }

        false // No violation found
    }
}
