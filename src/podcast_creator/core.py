import json
import re
import uuid
from pathlib import Path
from typing import Any, Dict, List, Literal, Tuple, Union

from langchain_core.output_parsers.pydantic import PydanticOutputParser
from loguru import logger
from moviepy import AudioFileClip, concatenate_audioclips
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
        ..., description="Size of the segment"
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
    Combines multiple audio files into a single MP3 file using moviepy.
    Expects 'audio_segments_data' in inputs: a list of strings, where each string is a path to an audio file.
    Also expects 'final_filename' in inputs: a string for the desired output filename (e.g., "podcast_episode.mp3").
    Example input: {
        "audio_segments_data": ["path/to/audio1.mp3", "path/to/audio2.mp3"],
        "final_filename": "my_podcast.mp3"
    }
    Output: {"combined_audio_path": "output/audio/my_podcast.mp3"}
    """
    logger.info("[Core Function] combine_audio_files called.")
    if isinstance(audio_dir, str):
        audio_dir = Path(audio_dir)
    if isinstance(final_output_dir, str):
        final_output_dir = Path(final_output_dir)
    list_of_audio_paths = sorted(audio_dir.glob("*.mp3"))
    output_filename_from_input = final_filename

    logger.debug(list_of_audio_paths)

    if not list_of_audio_paths:
        logger.warning(
            "combine_audio_files: No audio segment data (list of paths) provided."
        )
        return {"combined_audio_path": "ERROR: No audio segment data"}

    if not isinstance(list_of_audio_paths, list):
        logger.error(
            f"combine_audio_files: 'audio_segments_data' is not a list. Received: {type(list_of_audio_paths)}"
        )
        return {
            "combined_audio_path": "ERROR: audio_segments_data must be a list of file paths"
        }

    clips = []
    valid_clips = []
    for i, file_path in enumerate(list_of_audio_paths):
        if not isinstance(file_path, Path):
            logger.warning(
                f"combine_audio_files: Item {i} in audio_segments_data is not a string path: {file_path}. Skipping."
            )
            continue

        try:
            if file_path.exists() and file_path.is_file():
                clips.append(AudioFileClip(str(file_path)))
                valid_clips.append(clips[-1])  # Keep track of valid clips for later
            else:
                logger.error(
                    f"combine_audio_files: File not found or not a file: {file_path}"
                )
        except Exception as e:
            logger.error(
                f"combine_audio_files: Error loading audio clip {file_path}: {e}"
            )

    if not clips:
        logger.error("combine_audio_files: No valid audio clips could be loaded.")
        return {"combined_audio_path": "ERROR: No valid clips"}

    try:
        # Ensure all clips are closed after concatenation, even if it fails during the process.
        # MoviePy's concatenate_audioclips might not close source clips if it errors out mid-way.
        final_clip = concatenate_audioclips(clips)
    except Exception as e:
        logger.error(f"Error during concatenate_audioclips: {e}")
        for clip_obj in clips:
            try:
                clip_obj.close()
            except Exception as close_exc:
                logger.debug(f"Error closing clip during error handling: {close_exc}")
        return {"combined_audio_path": f"ERROR: Concatenation failed - {e}"}

    output_dir = final_output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    # Use the filename from input if provided, otherwise generate one.
    if output_filename_from_input and isinstance(output_filename_from_input, str):
        # Basic sanitization for filename (optional, depending on how robust it needs to be)
        # For now, assume it's a simple filename like 'episode.mp3'
        output_filename = Path(
            output_filename_from_input
        ).name  # Use only the filename part
        if not output_filename.endswith(".mp3"):
            output_filename += ".mp3"  # Ensure .mp3 extension
    else:
        output_filename = f"combined_{uuid.uuid4().hex}.mp3"
        logger.warning(
            f"'final_filename' not provided or invalid in inputs. Using generated name: {output_filename}"
        )

    output_path = output_dir / output_filename

    try:
        final_clip.write_audiofile(str(output_path), codec="mp3")
        logger.info(f"Successfully combined audio to: {output_path.resolve()}")
        return {
            "combined_audio_path": str(output_path.resolve()),
            "original_segments_count": len(valid_clips),
            "total_duration_seconds": final_clip.duration,
        }
    except Exception as e:
        logger.error(f"Error writing final audio file {output_path}: {e}")
        return {"combined_audio_path": f"ERROR: Failed to write output audio - {e}"}
    finally:
        final_clip.close()  # Close the final concatenated clip
        for clip_obj in clips:  # Ensure all source clips are closed
            try:
                clip_obj.close()
            except Exception as close_exc:
                logger.debug(f"Error closing source clip: {close_exc}")
