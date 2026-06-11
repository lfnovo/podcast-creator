"""
Tests for core utility functions
"""

import asyncio
import struct
import wave
from pathlib import Path

import pytest

from podcast_creator.core import (
    clean_thinking_content,
    combine_audio_files,
    extract_text_content,
    parse_thinking_content,
)


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


class TestParseThinkingContent:
    """Tests for parse_thinking_content and clean_thinking_content"""

    def test_closed_think_tags(self):
        """Standard <think>...</think> tags are removed"""
        content = '<think>Let me analyze this</think>{"answer": "yes"}'
        thinking, cleaned = parse_thinking_content(content)
        assert thinking == "Let me analyze this"
        assert cleaned == '{"answer": "yes"}'

    def test_no_think_tags(self):
        """Content without think tags is returned as-is"""
        content = '{"transcript": [{"speaker": "Alice", "dialogue": "Hello"}]}'
        thinking, cleaned = parse_thinking_content(content)
        assert thinking == ""
        assert cleaned == content

    def test_unclosed_think_tag_json_same_line(self):
        """Unclosed <think> with JSON starting on same line as thinking text"""
        content = (
            "<think>The user wants a podcast transcript.\n"
            "I need to focus on the key points.\n"
            "Speaker Roles:\n"
            "- Dr. Alex: Analytical\n"
            "- Jamie: Enthusiastic\n"
            "\n"
            'This will ensure at least 3 turns and cover all points.'
            '{"transcript": [{"speaker": "Alice", "dialogue": "Hello"}]}'
        )
        thinking, cleaned = parse_thinking_content(content)
        assert "<think>" not in cleaned
        assert '"transcript"' in cleaned
        assert "The user wants" in thinking

    def test_unclosed_think_tag_json_new_line(self):
        """Unclosed <think> without </think> followed by JSON on new line"""
        content = (
            "<think>\n"
            "Let me think about this carefully.\n"
            "I should create a natural dialogue.\n"
            "\n"
            '{"transcript": [{"speaker": "Alice", "dialogue": "Hi there!"}]}'
        )
        thinking, cleaned = parse_thinking_content(content)
        assert "<think>" not in cleaned
        assert '"transcript"' in cleaned
        assert "think about this carefully" in thinking

    def test_closed_think_tag_multiline(self):
        """Closed <think> tag with multi-line thinking then JSON"""
        content = (
            "<think>\n"
            "The user wants a podcast transcript for the first segment.\n"
            "I need to focus on:\n"
            "1. Introducing the topic\n"
            "2. Discussing the key points\n"
            "</think>\n"
            '{"transcript": [{"speaker": "Dr. Alex", "dialogue": "Welcome!"}]}'
        )
        thinking, cleaned = parse_thinking_content(content)
        assert "<think>" not in cleaned
        assert '"transcript"' in cleaned

    def test_unclosed_think_tag_no_json(self):
        """Unclosed <think> with no JSON content after it"""
        content = "<think>Just thinking, no output"
        thinking, cleaned = parse_thinking_content(content)
        assert "<think>" not in cleaned
        assert "Just thinking" in thinking

    def test_clean_thinking_content_unclosed(self):
        """clean_thinking_content convenience function handles unclosed tags"""
        content = (
            "<think>\n"
            "Some thinking here.\n"
            "\n"
            '{"transcript": [{"speaker": "Alice", "dialogue": "Hello"}]}'
        )
        cleaned = clean_thinking_content(content)
        assert "<think>" not in cleaned
        assert '"transcript"' in cleaned

    def test_non_string_input(self):
        """Non-string input is handled gracefully"""
        thinking, cleaned = parse_thinking_content(None)
        assert thinking == ""
        assert cleaned == ""

    def test_multiple_closed_think_tags(self):
        """Multiple closed think blocks are all removed"""
        content = "<think>First</think>Hello <think>Second</think>World"
        thinking, cleaned = parse_thinking_content(content)
        assert "First" in thinking
        assert "Second" in thinking
        assert cleaned == "Hello World"

    def test_realistic_deepseek_response(self):
        """Realistic DeepSeek-style response with long thinking and no closing tag"""
        content = (
            "<think>The user wants a podcast transcript for the first segment "
            "of an episode about SurrealDB 3.0.\n"
            "I need to focus on:\n"
            "1.  **Introducing SurrealDB 3.0's vision.**\n"
            "2.  **Discussing the pain points of multi-model applications.**\n"
            "\n"
            "**Speaker Roles:**\n"
            "*   **Dr. Alex Chen:** Senior AI researcher\n"
            "*   **Jamie Rodriguez:** Full-stack engineer\n"
            "\n"
            "This will ensure at least 3 turns and cover all points."
            '{"transcript": [\n'
            '    {\n'
            '        "speaker": "Dr. Alex Chen",\n'
            '        "dialogue": "Welcome to the podcast, everyone."\n'
            "    },\n"
            "    {\n"
            '        "speaker": "Jamie Rodriguez",\n'
            '        "dialogue": "Thanks for having me!"\n'
            "    }\n"
            "]}"
        )
        thinking, cleaned = parse_thinking_content(content)
        assert "<think>" not in cleaned
        assert '"transcript"' in cleaned
        assert "SurrealDB 3.0" in thinking
        # Verify the JSON is parseable
        import json
        parsed = json.loads(cleaned)
        assert len(parsed["transcript"]) == 2


def _write_silent_mp3(path: Path, duration_seconds: float) -> None:
    """Write a minimal valid MP3 file by encoding silence via wave + ffmpeg."""
    import subprocess

    wav_path = path.with_suffix(".wav")
    sample_rate = 44100
    num_samples = int(sample_rate * duration_seconds)
    with wave.open(str(wav_path), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(b"\x00\x00" * num_samples)

    subprocess.run(
        ["ffmpeg", "-i", str(wav_path), "-q:a", "9", str(path), "-y"],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    wav_path.unlink()


@pytest.mark.skipif(
    __import__("shutil").which("ffmpeg") is None,
    reason="ffmpeg not available",
)
class TestCombineAudioFiles:
    """Tests for combine_audio_files — verifies ffmpeg-based concatenation preserves full duration."""

    def test_combines_clips_and_preserves_full_duration(self, tmp_path):
        """
        Regression test: each clip must be included in full.

        Before the fix, moviepy read duration from MP3 headers. TTS-generated MP3s
        can have headers that under-report the real duration; moviepy would truncate
        each clip, causing mid-sentence cutoffs in the assembled output.
        ffmpeg reads actual sample data and is not affected by this.
        """
        clips_dir = tmp_path / "clips"
        clips_dir.mkdir()
        _write_silent_mp3(clips_dir / "0000.mp3", 2.0)
        _write_silent_mp3(clips_dir / "0001.mp3", 3.0)
        _write_silent_mp3(clips_dir / "0002.mp3", 1.5)

        result = asyncio.run(combine_audio_files(clips_dir, "episode.mp3", tmp_path))

        assert "ERROR" not in result["combined_audio_path"]
        output = Path(result["combined_audio_path"])
        assert output.exists()
        assert result["original_segments_count"] == 3
        assert result["total_duration_seconds"] == pytest.approx(6.5, abs=0.2)

    def test_returns_error_when_no_clips(self, tmp_path):
        empty_dir = tmp_path / "clips"
        empty_dir.mkdir()
        result = asyncio.run(combine_audio_files(empty_dir, "episode.mp3", tmp_path))
        assert "ERROR" in result["combined_audio_path"]

    def test_creates_output_directory(self, tmp_path):
        clips_dir = tmp_path / "clips"
        clips_dir.mkdir()
        _write_silent_mp3(clips_dir / "0000.mp3", 1.0)
        output_dir = tmp_path / "new" / "nested" / "dir"

        result = asyncio.run(combine_audio_files(clips_dir, "episode.mp3", output_dir))

        assert output_dir.exists()
        assert "ERROR" not in result["combined_audio_path"]

    def test_handles_relative_audio_dir(self, tmp_path, monkeypatch):
        """audio_dir passed as relative path must still resolve correctly."""
        clips_dir = tmp_path / "clips"
        clips_dir.mkdir()
        _write_silent_mp3(clips_dir / "0000.mp3", 1.0)
        monkeypatch.chdir(tmp_path)

        result = asyncio.run(combine_audio_files(Path("clips"), "episode.mp3", tmp_path))

        assert "ERROR" not in result["combined_audio_path"]
