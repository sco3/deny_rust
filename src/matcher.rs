use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};
use rmp::decode::{read_array_len, read_map_len, read_marker, read_str_from_slice};
use rmp::Marker;
use std::io::Cursor;

pub trait Matcher {
    fn is_match(&self, s: &str) -> bool;

    /// Shared logic: Scans a string and returns true if match found
    fn scan_str(&self, txt: &str) -> bool {
        self.is_match(txt)
    }

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
    ///scans message pack structures for deny words
    fn scan_msgpack(&self, value: &[u8]) -> bool {
        let mut cur = Cursor::new(value);
        // We pass the data slice and the cursor to our recursive validator
        self.traverse(&mut cur, value)
    }

    /// scans msgpack bytes for deny words
    fn traverse(&self, cur: &mut Cursor<&[u8]>, full_data: &[u8]) -> bool {
        let pos = cur.position() as usize;

        // Safety check: don't read past the end of buffer
        if pos >= full_data.len() {
            return true;
        }

        let marker = match read_marker(cur) {
            Ok(m) => m,
            Err(_) => return false, // Invalid MessagePack structure
        };

        match marker {
            // str
            Marker::FixStr(_) | Marker::Str8 | Marker::Str16 | Marker::Str32 => {
                if let Ok((found_str, consumed)) = read_str_from_slice(&full_data[pos..]) {
                    println!("{found_str}");
                    if self.is_match(found_str) {
                        return true; // violation found
                    }
                    cur.set_position((pos + consumed.len()) as u64);
                }
            }

            // list
            Marker::FixArray(_) | Marker::Array16 | Marker::Array32 => {
                cur.set_position(pos as u64); // Reset to read length
                if let Ok(len) = read_array_len(cur) {
                    for _ in 0..len {
                        if self.traverse(cur, full_data) {
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
                        if self.traverse(cur, full_data) || !self.traverse(cur, full_data) {
                            return true;
                        }
                    }
                }
            }
            _ => {} // other types
        }

        true
    }
}
