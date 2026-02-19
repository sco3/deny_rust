#!/usr/bin/env python3
"""
Comprehensive Python integration tests for deny_filter module.
Tests edge cases, error handling, and Python-specific behaviors.
"""

import pytest
from deny_filter import DenyList, DenyListDaac, DenyListRs


# Test all implementations
ALL_IMPLS = [DenyList, DenyListDaac, DenyListRs]


@pytest.mark.parametrize("impl", ALL_IMPLS, ids=lambda x: x.__name__)
class TestEdgeCases:
    """Test edge cases for all deny list implementations."""

    def test_empty_word_list(self, impl):
        """Test with empty word list."""
        deny_list = impl([])
        assert not deny_list.is_match("anything")
        assert not deny_list.is_match("")
        assert not deny_list.scan_str("test")
        assert not deny_list.scan({})
        assert not deny_list.scan_any([])

    def test_empty_string_input(self, impl):
        """Test with empty string input."""
        deny_list = impl(["test", "word"])
        assert not deny_list.is_match("")
        assert not deny_list.scan_str("")

    def test_single_character_words(self, impl):
        """Test single character words."""
        deny_list = impl(["a", "b", "x"])
        assert deny_list.is_match("a")
        assert deny_list.is_match("B")  # case insensitive
        assert deny_list.is_match("test a test")
        assert not deny_list.is_match("c")

    def test_unicode_characters(self, impl):
        """Test Unicode character handling."""
        deny_list = impl(["café", "日本語", "🔥"])
        assert deny_list.is_match("café")
        assert deny_list.is_match("CAFÉ")  # case insensitive
        assert deny_list.is_match("日本語")
        assert deny_list.is_match("🔥")
        assert deny_list.is_match("test 🔥 test")

    def test_special_characters(self, impl):
        """Test special characters and punctuation."""
        deny_list = impl([
            "test@email.com",
            "hello-world",
            "under_score",
            "dots.in.word"
        ])
        assert deny_list.is_match("test@email.com")
        assert deny_list.is_match("hello-world")
        assert deny_list.is_match("under_score")
        assert deny_list.is_match("dots.in.word")

    def test_very_long_strings(self, impl):
        """Test with very long strings."""
        deny_list = impl(["needle"])

        # Long string with needle at end
        long_string = "a" * 10000 + " needle"
        assert deny_list.is_match(long_string)

        # Long string without needle
        long_string_no_match = "b" * 10000
        assert not deny_list.is_match(long_string_no_match)

    def test_case_insensitivity(self, impl):
        """Test case insensitive matching."""
        deny_list = impl(["CaseSensitive", "UPPERCASE"])
        assert deny_list.is_match("casesensitive")
        assert deny_list.is_match("CASESENSITIVE")
        assert deny_list.is_match("CaSeSenSiTive")
        assert deny_list.is_match("uppercase")

    def test_whitespace_handling(self, impl):
        """Test whitespace in strings."""
        deny_list = impl(["word"])
        assert deny_list.is_match(" word ")
        assert deny_list.is_match("\tword\t")
        assert deny_list.is_match("\nword\n")
        assert deny_list.is_match("word\r\n")

    def test_substring_matching(self, impl):
        """Test substring matching behavior."""
        deny_list = impl(["cat"])
        assert deny_list.is_match("cat")  # exact
        assert deny_list.is_match("cats")  # start
        assert deny_list.is_match("scatter")  # middle
        assert deny_list.is_match("tomcat")  # end
        assert deny_list.is_match("the cat sat")  # word

    def test_multiple_words(self, impl):
        """Test multiple words in deny list."""
        deny_list = impl(["one", "two", "three"])
        assert deny_list.is_match("one")
        assert deny_list.is_match("two")
        assert deny_list.is_match("three")
        assert deny_list.is_match("one two three")
        assert not deny_list.is_match("four five six")

    def test_duplicate_words(self, impl):
        """Test duplicate words in list."""
        deny_list = impl(["duplicate", "duplicate", "other"])
        assert deny_list.is_match("duplicate")
        assert deny_list.is_match("other")

    def test_multiline_strings(self, impl):
        """Test multiline string handling."""
        deny_list = impl(["secret"])
        multiline = "line 1\nline 2 with secret\nline 3"
        assert deny_list.is_match(multiline)

        clean_multiline = "line 1\nline 2\nline 3"
        assert not deny_list.is_match(clean_multiline)


@pytest.mark.parametrize("impl", ALL_IMPLS, ids=lambda x: x.__name__)
class TestScanDict:
    """Test scan method with various dictionary structures."""

    def test_empty_dict(self, impl):
        """Test with empty dictionary."""
        deny_list = impl(["blocked"])
        assert not deny_list.scan({})

    def test_dict_with_match(self, impl):
        """Test dict with matching value."""
        deny_list = impl(["blocked"])
        assert deny_list.scan({"key": "blocked"})

    def test_dict_without_match(self, impl):
        """Test dict without matching value."""
        deny_list = impl(["blocked"])
        assert not deny_list.scan({"key": "allowed"})

    def test_dict_multiple_values_one_match(self, impl):
        """Test dict with multiple values, one matching."""
        deny_list = impl(["blocked"])
        assert deny_list.scan({
            "key1": "clean",
            "key2": "also clean",
            "key3": "blocked word"
        })

    def test_dict_with_non_string_values(self, impl):
        """Test dict with non-string values."""
        deny_list = impl(["match"])
        # Should only match the string value
        assert deny_list.scan({
            "str": "match",
            "num": 42,
            "float": 3.14,
            "bool": True,
            "none": None
        })

        # Dict with only non-string values should not match
        assert not deny_list.scan({
            "num": 123,
            "bool": False,
            "none": None
        })


@pytest.mark.parametrize("impl", ALL_IMPLS, ids=lambda x: x.__name__)
class TestScanAny:
    """Test scan_any method with nested structures."""

    def test_deeply_nested_dicts(self, impl):
        """Test deeply nested dictionaries."""
        deny_list = impl(["secret"])

        nested = {
            "level1": {
                "level2": {
                    "level3": "secret"
                }
            }
        }
        assert deny_list.scan_any(nested)

        clean_nested = {
            "level1": {
                "level2": {
                    "level3": "clean"
                }
            }
        }
        assert not deny_list.scan_any(clean_nested)

    def test_deeply_nested_lists(self, impl):
        """Test deeply nested lists."""
        deny_list = impl(["forbidden"])

        nested = [[["forbidden"]]]
        assert deny_list.scan_any(nested)

        clean_nested = [[["allowed"]]]
        assert not deny_list.scan_any(clean_nested)

    def test_mixed_nested_structures(self, impl):
        """Test mixed nested structures (dict -> list -> dict)."""
        deny_list = impl(["banned"])

        mixed = {
            "items": [
                {"key": "banned"}
            ]
        }
        assert deny_list.scan_any(mixed)

    def test_list_with_mixed_types(self, impl):
        """Test list with mixed types."""
        deny_list = impl(["match"])
        assert deny_list.scan_any([42, "match", True])
        assert not deny_list.scan_any([42, "clean", True])

    def test_empty_collections(self, impl):
        """Test empty collections."""
        deny_list = impl(["word"])
        assert not deny_list.scan_any([])
        assert not deny_list.scan_any({})
        assert not deny_list.scan_any([[]])

    def test_none_values(self, impl):
        """Test None values in collections."""
        deny_list = impl(["word"])
        assert not deny_list.scan_any(None)
        assert not deny_list.scan_any([None, None])
        assert not deny_list.scan_any({"key": None})

    def test_complex_real_world_structure(self, impl):
        """Test complex real-world-like structure."""
        deny_list = impl(["sensitive_data"])

        complex_structure = {
            "user": {
                "name": "John Doe",
                "emails": ["john@example.com", "doe@test.com"],
                "metadata": {
                    "tags": ["tag1", "tag2"],
                    "notes": "Contains sensitive_data"
                }
            },
            "settings": {
                "enabled": True,
                "count": 42
            }
        }
        assert deny_list.scan_any(complex_structure)


@pytest.mark.parametrize("impl", ALL_IMPLS, ids=lambda x: x.__name__)
class TestBoundaryConditions:
    """Test boundary conditions and performance edge cases."""

    def test_large_word_list(self, impl):
        """Test with large word list."""
        words = [f"word{i}" for i in range(5000)]
        deny_list = impl(words)

        assert deny_list.is_match("word0")
        assert deny_list.is_match("word2500")
        assert deny_list.is_match("word4999")
        assert not deny_list.is_match("word5000")

    def test_very_long_word(self, impl):
        """Test with very long word."""
        long_word = "a" * 1000
        deny_list = impl([long_word])
        assert deny_list.is_match(long_word)
        assert not deny_list.is_match("a" * 999)

    def test_many_short_words(self, impl):
        """Test many short words."""
        words = [chr(i) for i in range(ord('a'), ord('z') + 1)]
        deny_list = impl(words)
        assert deny_list.is_match("a")
        assert deny_list.is_match("z")
        assert not deny_list.is_match("1")


class TestMethodConsistency:
    """Test consistency across different methods."""

    @pytest.mark.parametrize("impl", ALL_IMPLS, ids=lambda x: x.__name__)
    def test_is_match_vs_scan_str(self, impl):
        """Ensure is_match and scan_str return same results."""
        deny_list = impl(["test"])
        test_strings = [
            "test",
            "this is a test",
            "no match here",
            "",
            "TEST",
        ]

        for s in test_strings:
            assert deny_list.is_match(s) == deny_list.scan_str(s), \
                f"is_match and scan_str disagree on: {s!r}"

    @pytest.mark.parametrize("impl", ALL_IMPLS, ids=lambda x: x.__name__)
    def test_is_match_vs_scan_any_string(self, impl):
        """Ensure is_match and scan_any(string) return same results."""
        deny_list = impl(["test"])
        test_strings = [
            "test",
            "this is a test",
            "no match here",
            "TEST",
        ]

        for s in test_strings:
            assert deny_list.is_match(s) == deny_list.scan_any(s), \
                f"is_match and scan_any disagree on: {s!r}"


class TestErrorHandling:
    """Test error handling and edge cases that might cause errors."""

    @pytest.mark.parametrize("impl", ALL_IMPLS, ids=lambda x: x.__name__)
    def test_invalid_input_types_is_match(self, impl):
        """Test that invalid types to is_match raise appropriate errors."""
        deny_list = impl(["test"])

        # is_match expects string, these should raise TypeError
        with pytest.raises(TypeError):
            deny_list.is_match(123)  # type: ignore

        with pytest.raises(TypeError):
            deny_list.is_match(None)  # type: ignore

        with pytest.raises(TypeError):
            deny_list.is_match(["list"])  # type: ignore

    @pytest.mark.parametrize("impl", ALL_IMPLS, ids=lambda x: x.__name__)
    def test_invalid_input_types_scan(self, impl):
        """Test that invalid types to scan raise appropriate errors."""
        deny_list = impl(["test"])

        # scan expects dict
        with pytest.raises(TypeError):
            deny_list.scan("not a dict")  # type: ignore

        with pytest.raises(TypeError):
            deny_list.scan(123)  # type: ignore


class TestImplementationSpecific:
    """Test implementation-specific behaviors."""

    def test_denylist_constructor(self):
        """Test DenyList constructor."""
        deny_list = DenyList(["word1", "word2"])
        assert deny_list.is_match("word1")

    def test_denylist_daac_constructor(self):
        """Test DenyListDaac constructor."""
        deny_list = DenyListDaac(["word1", "word2"])
        assert deny_list.is_match("word1")

    def test_denylist_rs_constructor(self):
        """Test DenyListRs constructor."""
        deny_list = DenyListRs(["word1", "word2"])
        assert deny_list.is_match("word1")


class TestRegressionCases:
    """Regression tests for specific bugs or issues."""

    @pytest.mark.parametrize("impl", ALL_IMPLS, ids=lambda x: x.__name__)
    def test_scan_dict_with_nested_non_strings(self, impl):
        """Regression: scan should handle nested non-string values gracefully."""
        deny_list = impl(["blocked"])

        # This should not crash and should not match
        test_dict = {
            "nested": {
                "num": 42,
                "list": [1, 2, 3]
            }
        }
        # scan only checks top-level values, so this should not match
        assert not deny_list.scan(test_dict)

    @pytest.mark.parametrize("impl", ALL_IMPLS, ids=lambda x: x.__name__)
    def test_consecutive_matches(self, impl):
        """Test string with consecutive matching words."""
        deny_list = impl(["bad"])
        assert deny_list.is_match("badbad")
        assert deny_list.is_match("bad bad bad")

    @pytest.mark.parametrize("impl", ALL_IMPLS, ids=lambda x: x.__name__)
    def test_overlapping_patterns(self, impl):
        """Test overlapping patterns in word list."""
        deny_list = impl(["abc", "bcd", "cde"])
        assert deny_list.is_match("abc")
        assert deny_list.is_match("bcd")
        assert deny_list.is_match("abcde")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])