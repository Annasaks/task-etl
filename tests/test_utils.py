"""Unit tests for transform/utils.py — the safe_int / safe_str helpers."""
from transform.utils import safe_int, safe_str


class TestSafeInt:
    def test_returns_int_unchanged(self):
        assert safe_int(76) == 76

    def test_casts_numeric_string(self):
        assert safe_int("76") == 76

    def test_returns_none_on_none(self):
        assert safe_int(None) is None

    def test_returns_none_on_empty_string(self):
        assert safe_int("") is None

    def test_returns_none_on_non_numeric_string(self):
        assert safe_int("abc") is None

    def test_returns_none_on_invalid_type(self):
        assert safe_int([1, 2]) is None


class TestSafeStr:
    def test_returns_string_unchanged(self):
        assert safe_str("hello") == "hello"

    def test_casts_int_to_string(self):
        assert safe_str(42) == "42"

    def test_returns_none_on_none(self):
        assert safe_str(None) is None

    def test_returns_none_on_empty_string(self):
        assert safe_str("") is None
