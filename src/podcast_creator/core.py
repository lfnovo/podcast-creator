import json
import re
import uuid
from pathlib import Path
from typing import Any, Dict, List, Literal, Tuple, Union

from langchain_core.output_parsers.pydantic import PydanticOutputParser
from loguru import logger
from pydantic import BaseModel, Field, field_validator

# Compile regex pattern once for better performance
THINK_PATTERN = re.compile(r"<think>(.*?)</think>", re.DOTALL)


def parse_thinking_content(content: str) -> Tuple[str, str]:
    """
    Parse message content to extract thinking content from <think> tags.

    Handles both closed tags (<think>...</think>) and unclosed tags
    (<think>... without closing tag) that some models produce.

    Args:
        content (str): The original message content

    Returns:
        Tuple[str, str]: (thinking_content, cleaned_content)
            - thinking_content: Content from within <think> tags
            - cleaned_content: Original content with <think> blocks removed

    Example:
        >>> content = "<think>Let me analyze this</think>Here's my answer"
        >>> thinking, cleaned = parse_thinking_content(content)
        >>> print(thinking)
        "Let me analyze this"
        >>> print(cleaned)
        "Here's my answer"
    """
    # Input validation
    if not isinstance(content, str):
        return "", str(content) if content is not None else ""

    # Limit processing for very large content (100KB limit)
    if len(content) > 100000:
        return "", content

    # Step 1: Handle closed <think>...</think> tags
    thinking_matches = THINK_PATTERN.findall(content)

    if thinking_matches:
        thinking_content = "\n\n".join(match.strip() for match in thinking_matches)
        cleaned_content = THINK_PATTERN.sub("", content)
    else:
        thinking_content = ""
        cleaned_content = content

    # Step 2: Handle unclosed <think> tags (no matching </think>)
    if "<think>" in cleaned_content:
        think_idx = cleaned_content.index("<think>")
        before = cleaned_content[:think_idx]
        after = cleaned_content[think_idx + len("<think>"):]

        # Find valid JSON in the remaining content using raw_decode,
        # which can parse JSON starting at any position and ignores trailing text.
        decoder = json.JSONDecoder()
        json_pos = None
        for m in re.finditer(r"[\{\[]", after):
            try:
                decoder.raw_decode(after, m.start())
                json_pos = m.start()
                break
            except (json.JSONDecodeError, ValueError):
                continue

        if json_pos is not None:
            unclosed_thinking = after[:json_pos].strip()
            json_content = after[json_pos:].strip()
            thinking_content = (
                (thinking_content + "\n\n" + unclosed_thinking).strip()
                if thinking_content
                else unclosed_thinking
            )
            cleaned_content = (before + json_content).strip()
        else:
            # No valid JSON found, treat everything after <think> as thinking
            unclosed_thinking = after.strip()
            thinking_content = (
                (thinking_content + "\n\n" + unclosed_thinking).strip()
                if thinking_content
                else unclosed_thinking
            )
            cleaned_content = before.strip()

    # Clean up extra whitespace
    cleaned_content = re.sub(r"\n\s*\n\s*\n", "\n\n", cleaned_content).strip()

    return thinking_content, cleaned_content


def clean_thinking_content(content: str) -> str:
    """
    Remove thinking content from AI responses, returning only the cleaned content.

    This is a convenience function for cases where you only need the cleaned
    content and don't need access to the thinking process.

    Args:
        content (str): The original message content with potential <think> tags

    Returns:
        str: Content with <think> blocks removed and whitespace cleaned

    Example:
        >>> content = "<think>Let me think...</think>Here's the answer"
        >>> clean_thinking_content(content)
        "Here's the answer"
    """
    _, cleaned_content = parse_thinking_content(content)
    return cleaned_content


def extract_text_content(content) -> str:
    """Extract text from AIMessage content that may be a string or structured list.

    Some LLM providers (e.g. Google Gemini, DeepSeek) return AIMessage.content
    as a list of content parts instead of a plain string. This function normalizes
    the content to a plain string before parsing.

    Args:
        content: The content from an AIMessage, which may be a string,
            a list of dicts with "text" keys, a list of strings, or None.

    Returns:
        str: The extracted text content as a plain string.
    """
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        text_parts = []
        for part in content:
            if isinstance(part, dict) and "text" in part:
                text_parts.append(part["text"])
            elif isinstance(part, str):
                text_parts.append(part)
        return "".join(text_parts)
    if content is None:
        return ""
    return str(content)


class Segment(BaseModel):
    name: str = Field(..., description="Name of the segment")
    description: str = Field(..., description="Description of the segment")
    size: Literal["short", "medium", "long"] = Field(
        default="medium", description="Size of the segment"
    )


class Outline(BaseModel):
    segments: list[Segment] = Field(..., description="List of segments")

    def model_dump(self, **kwargs) -> Dict[str, Any]:
        return {"segments": [segment.model_dump(**kwargs) for segment in self.segments]}


class Dialogue(BaseModel):
    speaker: str = Field(..., description="Speaker name")
    dialogue: str = Field(..., description="Dialogue")

    @field_validator("speaker")
    @classmethod
    def validate_speaker_name(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError("Speaker name cannot be empty")
        return v.strip()


class Transcript(BaseModel):
    transcript: list[Dialogue] = Field(..., description="Transcript")

    def model_dump(self, **kwargs) -> Dict[str, Any]:
        # Custom serialization: convert list of Dialogue models to list of dicts
        return {
            "transcript": [
                dialogue.model_dump(**kwargs) for dialogue in self.transcript
            ]
        }


def create_validated_transcript_parser(valid_speaker_names: List[str]):
    """
    Create a transcript parser that validates speaker names against a list of valid names

    Args:
        valid_speaker_names: List of valid speaker names

    Returns:
        PydanticOutputParser: Parser with speaker validation
    """

    class ValidatedDialogue(BaseModel):
        speaker: str = Field(..., description="Speaker name")
        dialogue: str = Field(..., description="Dialogue")

        @field_validator("speaker")
        @classmethod
        def validate_speaker_name(cls, v):
            if not v or len(v.strip()) == 0:
                raise ValueError("Speaker name cannot be empty")

            cleaned_name = v.strip()
            if cleaned_name not in valid_speaker_names:
                raise ValueError(
                    f"Invalid speaker name '{cleaned_name}'. Must be one of: {', '.join(valid_speaker_names)}"
                )

            return cleaned_name

    class ValidatedTranscript(BaseModel):
        transcript: list[ValidatedDialogue] = Field(..., description="Transcript")

        def model_dump(self, **kwargs) -> Dict[str, Any]:
            return {
                "transcript": [
                    dialogue.model_dump(**kwargs) for dialogue in self.transcript
                ]
            }

    return PydanticOutputParser(pydantic_object=ValidatedTranscript)


outline_parser = PydanticOutputParser(pydantic_object=Outline)
transcript_parser = PydanticOutputParser(pydantic_object=Transcript)


def get_outline_prompter():
    """Get outline prompter with configuration support."""
    from .config import ConfigurationManager

    config_manager = ConfigurationManager()
    return config_manager.get_template_prompter("outline", parser=outline_parser)


def get_transcript_prompter():
    """Get transcript prompter with configuration support."""
    from .config import ConfigurationManager

    config_manager = ConfigurationManager()
    return config_manager.get_template_prompter("transcript", parser=transcript_parser)


# Legacy exports for backward compatibility
outline_prompt = get_outline_prompter()
transcript_prompt = get_transcript_prompter()

# Legacy functions removed - use create_podcast from graph.py instead


async def combine_audio_files(
    audio_dir: Union[Path, str], final_filename: str, final_output_dir: Union[Path, str]
):
    """
    Combines multiple audio files into a single MP3 file using ffmpeg's concat demuxer.

    ffmpeg reads actual audio sample data rather than trusting the duration reported
    in MP3 file headers. Some TTS providers produce MP3 files where the header duration
    is shorter than the real audio; moviepy's AudioFileClip trusted those headers and
    truncated each clip accordingly, causing every speaker turn to be cut off mid-sentence
    in the assembled output. ffmpeg is unaffected by this and is already a required
    dependency (via moviepy), so no new dependencies are introduced.
    """
    import asyncio
    import os

    logger.info("[Core Function] combine_audio_files called.")
    audio_dir = Path(audio_dir).resolve()
    final_output_dir = Path(final_output_dir).resolve()

    list_of_audio_paths = sorted(audio_dir.glob("*.mp3"))
    logger.debug(list_of_audio_paths)

    if not list_of_audio_paths:
        logger.warning(
            "combine_audio_files: No audio segment data (list of paths) provided."
        )
        return {"combined_audio_path": "ERROR: No audio segment data"}

    final_output_dir.mkdir(parents=True, exist_ok=True)

    if final_filename and isinstance(final_filename, str):
        output_filename = Path(final_filename).name
        if not output_filename.endswith(".mp3"):
            output_filename += ".mp3"
    else:
        output_filename = f"combined_{uuid.uuid4().hex}.mp3"
        logger.warning(
            f"'final_filename' not provided or invalid. Using generated name: {output_filename}"
        )

    output_path = final_output_dir / output_filename
    concat_list_path = audio_dir / "_concat_list.txt"

    try:
        with open(str(concat_list_path), "w") as f:
            for path in list_of_audio_paths:
                f.write(f"file '{path.name}'\n")

        proc = await asyncio.create_subprocess_exec(
            "ffmpeg", "-f", "concat", "-safe", "0",
            "-i", str(concat_list_path),
            "-c", "copy", str(output_path), "-y",
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(audio_dir),
        )
        _, stderr = await proc.communicate()

        if proc.returncode != 0:
            error_text = stderr.decode(errors="replace")
            logger.error(f"combine_audio_files: ffmpeg concat failed: {error_text}")
            return {"combined_audio_path": f"ERROR: ffmpeg concat failed - {error_text}"}

        # Retrieve actual duration via ffprobe so callers get an accurate value.
        probe = await asyncio.create_subprocess_exec(
            "ffprobe", "-v", "quiet",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(output_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        probe_out, _ = await probe.communicate()
        try:
            total_duration = float(probe_out.decode().strip())
        except (ValueError, AttributeError):
            total_duration = 0.0

        logger.info(f"Successfully combined audio to: {output_path}")
        return {
            "combined_audio_path": str(output_path),
            "original_segments_count": len(list_of_audio_paths),
            "total_duration_seconds": total_duration,
        }
    except Exception as e:
        logger.error(f"combine_audio_files: unexpected error: {e}")
        return {"combined_audio_path": f"ERROR: {e}"}
    finally:
        try:
            concat_list_path.unlink(missing_ok=True)
        except Exception:
            pass
