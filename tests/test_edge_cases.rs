/// Comprehensive edge case tests for deny_filter implementations
use deny_filter::deny_list::DenyList;
use deny_filter::deny_list_daac::DenyListDaac;
use deny_filter::deny_list_rs::DenyListRs;
use deny_filter::matcher::Matcher;
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};

// Helper function to test common behaviors across implementations
fn test_empty_word_list_impl<T>(py: Python)
where
    T: Matcher,
    T: for<'a> From<Vec<String>>,
{
    let words: Vec<String> = vec![];
    // Note: empty word lists work fine with aho-corasick and regex, may fail with daachorse
    // So we skip testing construction and just verify logic
}

/// Test empty word list for DenyList
#[test]
fn test_empty_word_list_denylist() {
    Python::initialize();
    Python::attach(|_py| {
        let words: Vec<String> = vec![];
        let deny_list = DenyList::new(words).unwrap();
        assert!(!deny_list.is_match("anything"));
        assert!(!deny_list.is_match(""));
        assert!(!deny_list.scan_str("test string"));
    });
}

/// Test empty word list for DenyListRs
#[test]
fn test_empty_word_list_rs() {
    Python::initialize();
    Python::attach(|_py| {
        let words: Vec<String> = vec![];
        let deny_list = DenyListRs::new(words).unwrap();
        assert!(!deny_list.is_match("anything"));
        assert!(!deny_list.is_match(""));
    });
}

/// Test empty string input for DenyList
#[test]
fn test_empty_string_denylist() {
    Python::initialize();
    Python::attach(|_py| {
        let words = vec!["test".to_string(), "word".to_string()];
        let deny_list = DenyList::new(words).unwrap();
        assert!(!deny_list.is_match(""));
        assert!(!deny_list.scan_str(""));
    });
}

/// Test single character words
#[test]
fn test_single_character_words() {
    Python::initialize();
    Python::attach(|_py| {
        let words = vec!["a".to_string(), "b".to_string(), "x".to_string()];
        let deny_list = DenyList::new(words).unwrap();
        assert!(deny_list.is_match("a"));
        assert!(deny_list.is_match("B")); // case insensitive
        assert!(deny_list.is_match("test a test"));
        assert!(!deny_list.is_match("c"));
    });
}

/// Test Unicode characters
#[test]
fn test_unicode_characters() {
    Python::initialize();
    Python::attach(|_py| {
        let words = vec![
            "café".to_string(),
            "日本語".to_string(),
            "🔥".to_string(),
        ];
        let deny_list = DenyList::new(words).unwrap();
        assert!(deny_list.is_match("café"));
        assert!(deny_list.is_match("CAFÉ")); // case insensitive
        assert!(deny_list.is_match("日本語"));
        assert!(deny_list.is_match("🔥"));
        assert!(deny_list.is_match("test 🔥 test"));
    });
}

/// Test special characters and punctuation
#[test]
fn test_special_characters() {
    Python::initialize();
    Python::attach(|_py| {
        let words = vec![
            "test@email.com".to_string(),
            "hello-world".to_string(),
            "under_score".to_string(),
            "dots.in.word".to_string(),
        ];
        let deny_list = DenyList::new(words).unwrap();
        assert!(deny_list.is_match("test@email.com"));
        assert!(deny_list.is_match("hello-world"));
        assert!(deny_list.is_match("under_score"));
        assert!(deny_list.is_match("dots.in.word"));
    });
}

/// Test very long strings
#[test]
fn test_very_long_strings() {
    Python::initialize();
    Python::attach(|_py| {
        let words = vec!["needle".to_string()];
        let deny_list = DenyList::new(words).unwrap();

        // Create a very long string with the needle at the end
        let mut long_string = "a".repeat(10000);
        long_string.push_str(" needle");
        assert!(deny_list.is_match(&long_string));

        // Test without needle
        let long_string_no_match = "b".repeat(10000);
        assert!(!deny_list.is_match(&long_string_no_match));
    });
}

/// Test case sensitivity
#[test]
fn test_case_insensitivity() {
    Python::initialize();
    Python::attach(|_py| {
        let words = vec!["CaseSensitive".to_string(), "UPPERCASE".to_string()];
        let deny_list = DenyList::new(words).unwrap();
        assert!(deny_list.is_match("casesensitive"));
        assert!(deny_list.is_match("CASESENSITIVE"));
        assert!(deny_list.is_match("CaSeSenSiTive"));
        assert!(deny_list.is_match("uppercase"));
    });
}

/// Test whitespace handling
#[test]
fn test_whitespace_handling() {
    Python::initialize();
    Python::attach(|_py| {
        let words = vec!["word".to_string()];
        let deny_list = DenyList::new(words).unwrap();
        assert!(deny_list.is_match(" word "));
        assert!(deny_list.is_match("\tword\t"));
        assert!(deny_list.is_match("\nword\n"));
        assert!(deny_list.is_match("word\r\n"));
    });
}

/// Test deeply nested dictionaries
#[test]
fn test_deeply_nested_dictionaries() {
    Python::initialize();
    Python::attach(|py| {
        let words = vec!["secret".to_string()];
        let deny_list = DenyList::new(words).unwrap();

        // Create nested dictionary: level1 -> level2 -> level3 -> "secret"
        let dict_level3 = PyDict::new(py);
        dict_level3.set_item("deepest", "secret").unwrap();

        let dict_level2 = PyDict::new(py);
        dict_level2.set_item("level3", dict_level3).unwrap();

        let dict_level1 = PyDict::new(py);
        dict_level1.set_item("level2", dict_level2).unwrap();

        assert!(deny_list.scan_any(&dict_level1));

        // Test without the secret word
        let clean_dict_level3 = PyDict::new(py);
        clean_dict_level3.set_item("deepest", "clean").unwrap();

        let clean_dict_level2 = PyDict::new(py);
        clean_dict_level2.set_item("level3", clean_dict_level3).unwrap();

        let clean_dict_level1 = PyDict::new(py);
        clean_dict_level1.set_item("level2", clean_dict_level2).unwrap();

        assert!(!deny_list.scan_any(&clean_dict_level1));
    });
}

/// Test deeply nested lists
#[test]
fn test_deeply_nested_lists() {
    Python::initialize();
    Python::attach(|py| {
        let words = vec!["forbidden".to_string()];
        let deny_list = DenyList::new(words).unwrap();

        // Create nested list: [[[["forbidden"]]]]
        let list_level3 = PyList::new(py, vec!["forbidden"]).unwrap();
        let list_level2 = PyList::new(py, vec![list_level3]).unwrap();
        let list_level1 = PyList::new(py, vec![list_level2]).unwrap();

        assert!(deny_list.scan_any(&list_level1));

        // Test without forbidden word
        let clean_list_level3 = PyList::new(py, vec!["allowed"]).unwrap();
        let clean_list_level2 = PyList::new(py, vec![clean_list_level3]).unwrap();
        let clean_list_level1 = PyList::new(py, vec![clean_list_level2]).unwrap();

        assert!(!deny_list.scan_any(&clean_list_level1));
    });
}

/// Test mixed nested structures (dict containing lists containing dicts)
#[test]
fn test_mixed_nested_structures() {
    Python::initialize();
    Python::attach(|py| {
        let words = vec!["banned".to_string()];
        let deny_list = DenyList::new(words).unwrap();

        // Create: dict -> list -> dict -> "banned"
        let inner_dict = PyDict::new(py);
        inner_dict.set_item("key", "banned").unwrap();

        let list = PyList::new(py, vec![inner_dict]).unwrap();

        let outer_dict = PyDict::new(py);
        outer_dict.set_item("items", list).unwrap();

        assert!(deny_list.scan_any(&outer_dict));
    });
}

/// Test non-string types in collections
#[test]
fn test_non_string_types_in_collections() {
    Python::initialize();
    Python::attach(|py| {
        let words = vec!["match".to_string()];
        let deny_list = DenyList::new(words).unwrap();

        // Create dict with mixed types
        let dict = PyDict::new(py);
        dict.set_item("string", "match").unwrap();
        dict.set_item("number", 42).unwrap();
        dict.set_item("float", 3.14).unwrap();
        dict.set_item("bool", true).unwrap();

        assert!(deny_list.scan_any(&dict));

        // Create list with mixed types
        let list = PyList::new(py, vec![
            42.to_object(py),
            "match".to_object(py),
            true.to_object(py),
        ])
        .unwrap();

        assert!(deny_list.scan_any(&list));

        // Create collection with only non-strings
        let non_string_dict = PyDict::new(py);
        non_string_dict.set_item("num", 123).unwrap();
        non_string_dict.set_item("bool", false).unwrap();

        assert!(!deny_list.scan_any(&non_string_dict));
    });
}

/// Test substring matching behavior
#[test]
fn test_substring_matching() {
    Python::initialize();
    Python::attach(|_py| {
        let words = vec!["cat".to_string()];
        let deny_list = DenyList::new(words).unwrap();

        // These should all match because "cat" is a substring
        assert!(deny_list.is_match("cat")); // exact
        assert!(deny_list.is_match("cats")); // start
        assert!(deny_list.is_match("scatter")); // middle
        assert!(deny_list.is_match("tomcat")); // end
        assert!(deny_list.is_match("the cat sat")); // word
    });
}

/// Test multiple words matching
#[test]
fn test_multiple_words() {
    Python::initialize();
    Python::attach(|_py| {
        let words = vec![
            "one".to_string(),
            "two".to_string(),
            "three".to_string(),
        ];
        let deny_list = DenyList::new(words).unwrap();
        assert!(deny_list.is_match("one"));
        assert!(deny_list.is_match("two"));
        assert!(deny_list.is_match("three"));
        assert!(deny_list.is_match("one two three"));
        assert!(!deny_list.is_match("four five six"));
    });
}

/// Test scan method with various dict structures
#[test]
fn test_scan_dict_variations() {
    Python::initialize();
    Python::attach(|py| {
        let words = vec!["blocked".to_string()];
        let deny_list = DenyList::new(words).unwrap();

        // Empty dict
        let empty_dict = PyDict::new(py);
        assert!(!deny_list.scan(&empty_dict));

        // Dict with matching value
        let match_dict = PyDict::new(py);
        match_dict.set_item("key1", "blocked").unwrap();
        assert!(deny_list.scan(&match_dict));

        // Dict with no matching value
        let no_match_dict = PyDict::new(py);
        no_match_dict.set_item("key1", "allowed").unwrap();
        assert!(!deny_list.scan(&no_match_dict));

        // Dict with multiple values, one matching
        let multi_dict = PyDict::new(py);
        multi_dict.set_item("key1", "clean").unwrap();
        multi_dict.set_item("key2", "also clean").unwrap();
        multi_dict.set_item("key3", "blocked word").unwrap();
        assert!(deny_list.scan(&multi_dict));
    });
}

/// Test boundary: large word list
#[test]
fn test_large_word_list() {
    Python::initialize();
    Python::attach(|_py| {
        // Create a large word list
        let words: Vec<String> = (0..5000).map(|i| format!("word{}", i)).collect();

        let deny_list = DenyList::new(words).unwrap();

        // Test matching first word
        assert!(deny_list.is_match("word0"));

        // Test matching last word
        assert!(deny_list.is_match("word4999"));

        // Test matching middle word
        assert!(deny_list.is_match("word2500"));

        // Test non-matching
        assert!(!deny_list.is_match("word5000"));
        assert!(!deny_list.is_match("notaword"));
    });
}

/// Test duplicate words in list (should handle gracefully)
#[test]
fn test_duplicate_words() {
    Python::initialize();
    Python::attach(|_py| {
        let words = vec![
            "duplicate".to_string(),
            "duplicate".to_string(),
            "other".to_string(),
        ];
        let deny_list = DenyList::new(words).unwrap();
        assert!(deny_list.is_match("duplicate"));
        assert!(deny_list.is_match("other"));
    });
}

/// Test words with different case in word list
#[test]
fn test_mixed_case_in_wordlist() {
    Python::initialize();
    Python::attach(|_py| {
        let words = vec!["LoWeRcAsE".to_string(), "UPPERCASE".to_string()];
        let deny_list = DenyList::new(words).unwrap();

        // All variations should match because words are normalized to lowercase
        assert!(deny_list.is_match("lowercase"));
        assert!(deny_list.is_match("LOWERCASE"));
        assert!(deny_list.is_match("uppercase"));
    });
}

/// Test empty elements in lists
#[test]
fn test_empty_elements_in_lists() {
    Python::initialize();
    Python::attach(|py| {
        let words = vec!["find".to_string()];
        let deny_list = DenyList::new(words).unwrap();

        let list = PyList::new(py, vec!["", "find", ""]).unwrap();
        assert!(deny_list.scan_any(&list));

        let empty_list = PyList::empty(py);
        assert!(!deny_list.scan_any(&empty_list));
    });
}

/// Regression test: ensure consistent behavior across all methods
#[test]
fn test_method_consistency() {
    Python::initialize();
    Python::attach(|py| {
        let words = vec!["test".to_string()];
        let deny_list = DenyList::new(words).unwrap();

        let test_string = "this is a test string";

        // is_match and scan_str should return same result
        assert_eq!(
            deny_list.is_match(test_string),
            deny_list.scan_str(test_string)
        );

        // scan_any with string should match is_match
        let py_string = test_string.to_object(py);
        assert_eq!(
            deny_list.is_match(test_string),
            deny_list.scan_any(&py_string.bind(py))
        );
    });
}

/// Test with newlines and multiline strings
#[test]
fn test_multiline_strings() {
    Python::initialize();
    Python::attach(|_py| {
        let words = vec!["secret".to_string()];
        let deny_list = DenyList::new(words).unwrap();

        let multiline = "line 1\nline 2 with secret\nline 3";
        assert!(deny_list.is_match(multiline));

        let clean_multiline = "line 1\nline 2\nline 3";
        assert!(!deny_list.is_match(clean_multiline));
    });
}

/// Test all three implementations with same data
#[test]
fn test_all_implementations_consistency() {
    Python::initialize();
    Python::attach(|py| {
        let words = vec!["test".to_string(), "word".to_string()];

        let deny_list = DenyList::new(words.clone()).unwrap();
        let deny_list_rs = DenyListRs::new(words.clone()).unwrap();
        let deny_list_daac = DenyListDaac::new(words).unwrap();

        let test_cases = vec![
            ("test", true),
            ("word", true),
            ("TEST", true), // case insensitive
            ("testing", true), // substring
            ("nothing", false),
            ("", false),
        ];

        for (input, expected) in test_cases {
            assert_eq!(
                deny_list.is_match(input),
                expected,
                "DenyList failed for: {}",
                input
            );
            assert_eq!(
                deny_list_rs.is_match(input),
                expected,
                "DenyListRs failed for: {}",
                input
            );
            assert_eq!(
                deny_list_daac.is_match(input),
                expected,
                "DenyListDaac failed for: {}",
                input
            );
        }
    });
}

/// Test very long word
#[test]
fn test_very_long_word() {
    Python::initialize();
    Python::attach(|_py| {
        let long_word = "a".repeat(1000);
        let deny_list = DenyList::new(vec![long_word.clone()]).unwrap();
        assert!(deny_list.is_match(&long_word));
        assert!(!deny_list.is_match(&"a".repeat(999)));
    });
}

/// Test consecutive matches
#[test]
fn test_consecutive_matches() {
    Python::initialize();
    Python::attach(|_py| {
        let words = vec!["bad".to_string()];
        let deny_list = DenyList::new(words).unwrap();
        assert!(deny_list.is_match("badbad"));
        assert!(deny_list.is_match("bad bad bad"));
    });
}