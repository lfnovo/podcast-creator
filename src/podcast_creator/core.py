import asyncio
import json
import os
import re
import uuid
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Tuple, Union

from imageio_ffmpeg import get_ffmpeg_exe  # type: ignore[import-untyped]
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


AUDIO_STREAM_PATTERN = re.compile(r"Audio: [^,]+, (\d+) Hz, ([^,]+),")
OUT_TIME_PATTERN = re.compile(r"^out_time_us=(\d+)$", re.MULTILINE)


async def _run_ffmpeg(args: List[str]) -> Tuple[int, str, str]:
    """Run ffmpeg with the given arguments and return (returncode, stdout, stderr).

    The child never reads the parent's stdin and is killed if the caller is cancelled.
    """
    process = await asyncio.create_subprocess_exec(
        get_ffmpeg_exe(),
        *args,
        stdin=asyncio.subprocess.DEVNULL,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await process.communicate()
    except asyncio.CancelledError:
        if process.returncode is None:
            process.kill()
            await process.wait()
        raise
    return (
        process.returncode if process.returncode is not None else -1,
        stdout.decode(errors="replace"),
        stderr.decode(errors="replace"),
    )


async def _probe_audio_format(file_path: Path) -> Optional[Tuple[int, str]]:
    """Return (sample_rate, channel_layout) of the first audio stream, if detectable."""
    _, _, stderr = await _run_ffmpeg(["-hide_banner", "-nostdin", "-i", str(file_path)])
    match = AUDIO_STREAM_PATTERN.search(stderr)
    if not match:
        return None
    layout = match.group(2).strip().split("(")[0].strip()
    return int(match.group(1)), layout


def _build_concat_filter(
    num_inputs: int, audio_format: Optional[Tuple[int, str]]
) -> str:
    """Build a filter graph that resets each input's timestamps and concatenates them.

    Resetting PTS per input makes the concat follow the decoded audio instead of the
    (often inaccurate) duration declared in TTS-generated MP3 headers. When the format of
    the first clip is known, every input is normalized to it so clips from different TTS
    providers can be concatenated.
    """
    normalize = ""
    if audio_format:
        sample_rate, layout = audio_format
        normalize = (
            f"aresample={sample_rate},"
            f"aformat=sample_rates={sample_rate}:channel_layouts={layout},"
        )
    chains = [f"[{i}:a]{normalize}asetpts=PTS-STARTPTS[a{i}]" for i in range(num_inputs)]
    labels = "".join(f"[a{i}]" for i in range(num_inputs))
    return ";".join(chains) + f";{labels}concat=n={num_inputs}:v=0:a=1[out]"


async def combine_audio_files(
    audio_dir: Union[Path, str], final_filename: str, final_output_dir: Union[Path, str]
) -> Dict[str, Any]:
    """
    Combine every .mp3 clip in ``audio_dir`` (sorted by name) into a single MP3 file.

    Uses a single ffmpeg process with the concat filter, so the number of processes does
    not grow with the number of clips, and every clip is decoded to its real end even when
    its MP3 header declares a wrong duration.

    Args:
        audio_dir: Directory containing the clips to combine.
        final_filename: Name of the output file; ".mp3" is appended when missing.
        final_output_dir: Directory where the combined file is written.

    Returns:
        Dict with "combined_audio_path", "original_segments_count" and
        "total_duration_seconds".

    Raises:
        ValueError: If there are no clips to combine.
        RuntimeError: If ffmpeg fails to combine the clips.
    """
    logger.info("[Core Function] combine_audio_files called.")
    audio_dir = Path(audio_dir)
    final_output_dir = Path(final_output_dir)
    clip_paths = sorted(p for p in audio_dir.glob("*.mp3") if p.is_file())

    logger.debug(clip_paths)

    if not clip_paths:
        raise ValueError(f"combine_audio_files: no .mp3 clips found in {audio_dir}")

    final_output_dir.mkdir(parents=True, exist_ok=True)

    if final_filename and isinstance(final_filename, str):
        output_filename = Path(final_filename).name  # Use only the filename part
        if not output_filename.endswith(".mp3"):
            output_filename += ".mp3"
    else:
        output_filename = f"combined_{uuid.uuid4().hex}.mp3"
        logger.warning(
            f"'final_filename' not provided or invalid. Using generated name: {output_filename}"
        )

    output_path = final_output_dir / output_filename
    # Write to a temporary file so a failed run never touches an existing episode
    temp_path = final_output_dir / f".{output_filename}.{uuid.uuid4().hex}.tmp"

    succeeded = False
    try:
        audio_format = await _probe_audio_format(clip_paths[0])
        if audio_format is None:
            logger.warning(
                f"combine_audio_files: could not detect audio format of {clip_paths[0]}; "
                "concatenating without normalization"
            )

        args = ["-hide_banner", "-nostdin", "-y"]
        for clip_path in clip_paths:
            args += ["-i", str(clip_path)]
        args += [
            "-filter_complex",
            _build_concat_filter(len(clip_paths), audio_format),
            "-map",
            "[out]",
            "-c:a",
            "libmp3lame",
            "-b:a",
            "128k",
            "-progress",
            "pipe:1",
            "-nostats",
            "-f",
            "mp3",
            str(temp_path),
        ]

        returncode, stdout, stderr = await _run_ffmpeg(args)

        if returncode != 0:
            error_tail = "\n".join(stderr.strip().splitlines()[-20:])
            raise RuntimeError(
                f"combine_audio_files: ffmpeg exited with code {returncode} while "
                f"combining {len(clip_paths)} clips:\n{error_tail}"
            )
        os.replace(temp_path, output_path)
        succeeded = True
    except OSError as e:
        raise RuntimeError(f"combine_audio_files: failed to run ffmpeg: {e}") from e
    finally:
        # Remove partial output on any failure, including cancellation
        if not succeeded:
            temp_path.unlink(missing_ok=True)

    out_times = OUT_TIME_PATTERN.findall(stdout)
    total_duration = int(out_times[-1]) / 1_000_000 if out_times else None

    logger.info(f"Successfully combined audio to: {output_path.resolve()}")
    return {
        "combined_audio_path": str(output_path.resolve()),
        "original_segments_count": len(clip_paths),
        "total_duration_seconds": total_duration,
    }
