"""
Tests for core utility functions
"""

from podcast_creator.core import extract_text_content


class TestExtractTextContent:
    """Tests for extract_text_content function"""

    def test_string_passthrough(self):
        """Plain string content is returned as-is"""
        assert extract_text_content("hello world") == "hello world"

    def test_gemini_format(self):
        """Structured list with dict parts containing 'text' key (Gemini-style)"""
        content = [
            {"type": "text", "text": "hello world", "extras": {"some": "data"}}
        ]
        assert extract_text_content(content) == "hello world"

    def test_gemini_format_multiple_parts(self):
        """Multiple structured dict parts are concatenated"""
        content = [
            {"type": "text", "text": "hello "},
            {"type": "text", "text": "world"},
        ]
        assert extract_text_content(content) == "hello world"

    def test_list_of_strings(self):
        """List of plain strings is concatenated"""
        assert extract_text_content(["hello", " world"]) == "hello world"

    def test_mixed_list(self):
        """Mixed list of dicts and strings is handled correctly"""
        content = [
            {"type": "text", "text": "hello "},
            "world",
        ]
        assert extract_text_content(content) == "hello world"

    def test_empty_string(self):
        """Empty string returns empty string"""
        assert extract_text_content("") == ""

    def test_empty_list(self):
        """Empty list returns empty string"""
        assert extract_text_content([]) == ""

    def test_none(self):
        """None returns empty string"""
        assert extract_text_content(None) == ""

    def test_non_string_non_list_fallback(self):
        """Non-string, non-list types fall back to str()"""
        assert extract_text_content(42) == "42"

    def test_dict_without_text_key_skipped(self):
        """Dict items without 'text' key are skipped"""
        content = [
            {"type": "image", "url": "http://example.com"},
            {"type": "text", "text": "hello"},
        ]
        assert extract_text_content(content) == "hello"
