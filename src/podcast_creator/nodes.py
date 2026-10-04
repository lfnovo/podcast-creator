import asyncio
import os
from pathlib import Path
from typing import Any, Dict, List

from esperanto import AIFactory
from esperanto.providers.llm.structured_output import is_json_schema_unsupported_error
from langchain_core.runnables import RunnableConfig
from loguru import logger

from .core import (
    Dialogue,
    clean_thinking_content,
    combine_audio_files,
    create_validated_transcript_parser,
    extract_text_content,
    get_outline_prompter,
    get_transcript_prompter,
    outline_parser,
)
from .defaults import DEFAULT_AUDIO_GAP_MS, validate_audio_gap_ms
from .retry import create_retry_decorator, get_retry_config
from .state import PodcastState

# Default output token limits; override via outline_config / transcript_config.
# 8192 fits the bundled default models (gpt-4o-mini for outlines, claude-sonnet-5-5 for
# transcripts). Models with a lower output cap need an explicit lower max_tokens.
DEFAULT_OUTLINE_MAX_TOKENS = 8192
DEFAULT_TRANSCRIPT_MAX_TOKENS = 8192


_RESPONSE_FORMAT_REJECTION_SIGNALS = (
    "unavailable",
    "unsupported",
    "not support",
    "not implemented",
    "must be 'text'",
    'must be "text"',
)


def _is_json_schema_rejection(error: BaseException) -> bool:
    """Whether a provider error means the endpoint can't do json_schema structured output.

    Uses esperanto's shared detection, plus HTTP 400 errors that say the
    ``response_format`` is unavailable or unsupported without naming ``json_schema``
    (e.g. "This response_format type is unavailable now"). A 400 that merely
    mentions ``response_format`` (a proxy echoing the request body) does not count.
    """
    if isinstance(error, Exception) and is_json_schema_unsupported_error(error):
        return True
    status_code = getattr(error, "status_code", None)
    if status_code is None:
        status_code = getattr(getattr(error, "response", None), "status_code", None)
    if status_code != 400:
        return False
    message = str(error).lower()
    return "response_format" in message and any(
        signal in message for signal in _RESPONSE_FORMAT_REJECTION_SIGNALS
    )


class _SchemaFallbackModel:
    """LangChain chat model that requests json_schema and falls back to generic JSON.

    The fallback applies only when the caller did not set ``structured`` explicitly,
    happens at most once, and is remembered through ``json_mode_models`` so later
    calls in the same run go straight to generic JSON.
    """

    def __init__(
        self,
        provider: str,
        model_name: str,
        max_tokens: int,
        schema: Any,
        user_config: Dict[str, Any],
        json_mode_models: List[str],
    ):
        self.provider = provider
        self.model_name = model_name
        self.key = f"{provider}/{model_name}"
        self.uses_default_schema = "structured" not in user_config
        self.json_mode = self.uses_default_schema and self.key in json_mode_models
        self._config = {
            "max_tokens": max_tokens,
            "structured": {"type": "json"}
            if self.json_mode
            else {"type": "json_schema", "schema": schema},
            **user_config,
        }
        self._model = self._create(self._config)

    def _create(self, config: Dict[str, Any]) -> Any:
        return AIFactory.create_language(
            self.provider, self.model_name, config=config
        ).to_langchain()

    async def ainvoke(self, prompt_text: str) -> Any:
        try:
            return await self._model.ainvoke(prompt_text)
        except Exception as error:
            if (
                not self.uses_default_schema
                or self.json_mode
                or not _is_json_schema_rejection(error)
            ):
                raise
            logger.warning(
                f"{self.key} rejected json_schema structured output; "
                "retrying in generic JSON mode. "
                f"Original error: {error}"
            )
            json_model = self._create({**self._config, "structured": {"type": "json"}})
            result = await json_model.ainvoke(prompt_text)
            # Commit the downgrade only once generic JSON actually worked
            self._model = json_model
            self.json_mode = True
            return result


def _json_mode_models(state: PodcastState, *models: _SchemaFallbackModel) -> List[str]:
    keys = list(state.get("json_mode_models") or [])
    for model in models:
        if model.json_mode and model.uses_default_schema and model.key not in keys:
            keys.append(model.key)
    return keys


async def generate_outline_node(state: PodcastState, config: RunnableConfig) -> Dict:
    """Generate podcast outline from content and briefing"""
    logger.info("Starting outline generation")

    configurable = config.get("configurable", {})
    outline_provider = configurable.get("outline_provider", "openai")
    outline_model_name = configurable.get("outline_model", "gpt-4o-mini")
    outline_config = configurable.get("outline_config") or {}

    # Create outline model (json_schema, with a generic JSON fallback)
    outline_model = _SchemaFallbackModel(
        outline_provider,
        outline_model_name,
        DEFAULT_OUTLINE_MAX_TOKENS,
        outline_parser.pydantic_object,
        outline_config,
        state.get("json_mode_models") or [],
    )

    # Build retry decorator from configurable settings
    retry_cfg = get_retry_config(configurable)
    llm_retry = create_retry_decorator(**retry_cfg)

    @llm_retry
    async def _invoke_and_parse(prompt_text: str):
        result = await outline_model.ainvoke(prompt_text)
        content = extract_text_content(result.content)
        content = clean_thinking_content(content)
        return outline_parser.invoke(content)

    # Generate outline
    outline_prompt = get_outline_prompter()
    outline_prompt_text = outline_prompt.render(
        {
            "briefing": state["briefing"],
            "num_segments": state["num_segments"],
            "context": state["content"],
            "speakers": state["speaker_profile"].speakers
            if state["speaker_profile"]
            else [],
            "language": state.get("language"),
        }
    )

    outline_result = await _invoke_and_parse(outline_prompt_text)

    logger.info(f"Generated outline with {len(outline_result.segments)} segments")

    return {
        "outline": outline_result,
        "json_mode_models": _json_mode_models(state, outline_model),
    }


async def generate_transcript_node(state: PodcastState, config: RunnableConfig) -> Dict:
    """Generate conversational transcript from outline"""
    logger.info("Starting transcript generation")

    assert state.get("outline") is not None, "outline must be provided"
    assert state.get("speaker_profile") is not None, "speaker_profile must be provided"

    configurable = config.get("configurable", {})
    transcript_provider: str = configurable.get("transcript_provider", "openai")
    transcript_model_name: str = configurable.get("transcript_model", "gpt-4o-mini")
    transcript_config = configurable.get("transcript_config") or {}

    # Create validated transcript parser
    speaker_profile = state["speaker_profile"]
    assert speaker_profile is not None, "speaker_profile must be provided"
    speaker_names = speaker_profile.get_speaker_names()
    validated_transcript_parser = create_validated_transcript_parser(speaker_names)

    # Create transcript model (json_schema, with a generic JSON fallback)
    transcript_model = _SchemaFallbackModel(
        transcript_provider,
        transcript_model_name,
        DEFAULT_TRANSCRIPT_MAX_TOKENS,
        validated_transcript_parser.pydantic_object,
        transcript_config,
        state.get("json_mode_models") or [],
    )

    # Build retry decorator from configurable settings
    retry_cfg = get_retry_config(configurable)
    llm_retry = create_retry_decorator(**retry_cfg)

    @llm_retry
    async def _invoke_and_parse(prompt_text: str):
        result = await transcript_model.ainvoke(prompt_text)
        content = extract_text_content(result.content)
        content = clean_thinking_content(content)
        return validated_transcript_parser.invoke(content)

    # Generate transcript for each segment
    outline = state["outline"]
    assert outline is not None, "outline must be provided"

    transcript: List[Dialogue] = []
    for i, segment in enumerate(outline.segments):
        logger.info(
            f"Generating transcript for segment {i + 1}/{len(outline.segments)}: {segment.name}"
        )

        is_final = i == len(outline.segments) - 1
        turns = 3 if segment.size == "short" else 6 if segment.size == "medium" else 10

        data = {
            "briefing": state["briefing"],
            "outline": outline,
            "context": state["content"],
            "segment": segment,
            "is_final": is_final,
            "turns": turns,
            "speakers": speaker_profile.speakers,
            "speaker_names": speaker_names,
            "transcript": transcript,
            "language": state.get("language"),
        }

        transcript_prompt = get_transcript_prompter()
        transcript_prompt_rendered = transcript_prompt.render(data)
        result = await _invoke_and_parse(transcript_prompt_rendered)
        transcript.extend(result.transcript)

    logger.info(f"Generated transcript with {len(transcript)} dialogue segments")

    return {
        "transcript": transcript,
        "json_mode_models": _json_mode_models(state, transcript_model),
    }


def route_audio_generation(state: PodcastState, config: RunnableConfig) -> str:
    """Route to sequential batch processing of audio generation"""
    transcript = state["transcript"]
    total_segments = len(transcript)

    logger.info(
        f"Routing {total_segments} dialogue segments for sequential batch processing"
    )

    # Return node name for sequential processing
    return "generate_all_audio"


async def generate_all_audio_node(state: PodcastState, config: RunnableConfig) -> Dict:
    """Generate all audio clips using sequential batches to respect API limits"""
    transcript = state["transcript"]
    output_dir = state["output_dir"]
    total_segments = len(transcript)

    # Get batch size from environment variable, default to 5
    batch_size = int(os.getenv("TTS_BATCH_SIZE", "5"))
    logger.info(f"Using TTS batch size: {batch_size}")

    assert state.get("speaker_profile") is not None, "speaker_profile must be provided"

    # Get TTS configuration from speaker profile
    speaker_profile = state["speaker_profile"]
    assert speaker_profile is not None, "speaker_profile must be provided"
    tts_provider = speaker_profile.tts_provider
    tts_model = speaker_profile.tts_model
    voices = speaker_profile.get_voice_mapping()
    tts_config = speaker_profile.tts_config or {}

    # Build retry decorator from configurable settings
    configurable = config.get("configurable", {})
    retry_cfg = get_retry_config(configurable)
    tts_retry = create_retry_decorator(**retry_cfg)

    @tts_retry
    async def _generate_clip(dialogue_info: Dict) -> Path:
        return await generate_single_audio_clip(dialogue_info)

    logger.info(
        f"Generating {total_segments} audio clips in sequential batches of {batch_size}"
    )

    all_clip_paths = []

    # Process in sequential batches
    for batch_start in range(0, total_segments, batch_size):
        batch_end = min(batch_start + batch_size, total_segments)
        batch_number = batch_start // batch_size + 1
        total_batches = (total_segments + batch_size - 1) // batch_size

        logger.info(
            f"Processing batch {batch_number}/{total_batches} (clips {batch_start}-{batch_end - 1})"
        )

        # Create tasks for this batch
        batch_tasks = []
        for i in range(batch_start, batch_end):
            speaker = speaker_profile.get_speaker_by_name(transcript[i].speaker)
            dialogue_info = {
                "dialogue": transcript[i],
                "index": i,
                "output_dir": output_dir,
                "tts_provider": speaker.tts_provider or tts_provider,
                "tts_model": speaker.tts_model or tts_model,
                "voices": voices,
                "tts_config": speaker.tts_config if speaker.tts_config is not None else tts_config,
            }
            task = _generate_clip(dialogue_info)
            batch_tasks.append(task)

        # Process this batch concurrently (but wait before next batch)
        batch_clip_paths = await asyncio.gather(*batch_tasks)
        all_clip_paths.extend(batch_clip_paths)

        logger.info(f"Completed batch {batch_number}/{total_batches}")

        # Small delay between batches to be extra safe with API limits
        if batch_end < total_segments:
            await asyncio.sleep(1)

    logger.info(f"Generated all {len(all_clip_paths)} audio clips")

    return {"audio_clips": all_clip_paths}


async def generate_single_audio_clip(dialogue_info: Dict) -> Path:
    """Generate a single audio clip"""
    dialogue = dialogue_info["dialogue"]
    index = dialogue_info["index"]
    output_dir = dialogue_info["output_dir"]
    tts_provider = dialogue_info["tts_provider"]
    tts_model_name = dialogue_info["tts_model"]
    voices = dialogue_info["voices"]
    tts_config = dict(dialogue_info.get("tts_config") or {})

    logger.info(f"Generating audio clip {index:04d} for {dialogue.speaker}")

    # Create clips directory
    clips_dir = output_dir / "clips"
    clips_dir.mkdir(exist_ok=True, parents=True)

    # Generate filename
    filename = f"{index:04d}.mp3"
    clip_path = clips_dir / filename

    # Extract named params from tts_config, pass rest as kwargs
    api_key = tts_config.pop("api_key", None)
    base_url = tts_config.pop("base_url", None)

    # Create TTS model
    tts_model = AIFactory.create_text_to_speech(
        tts_provider, tts_model_name, api_key=api_key, base_url=base_url, **tts_config
    )

    # Generate audio
    await tts_model.agenerate_speech(
        text=dialogue.dialogue, voice=voices[dialogue.speaker], output_file=clip_path
    )

    logger.info(f"Generated audio clip: {clip_path}")

    return clip_path


async def combine_audio_node(state: PodcastState, config: RunnableConfig) -> Dict:
    """Combine all audio clips into final podcast episode"""
    logger.info("Starting audio combination")

    clips_dir = state["output_dir"] / "clips"
    audio_dir = state["output_dir"] / "audio"
    gap_ms = config.get("configurable", {}).get("audio_gap_ms")
    if gap_ms is None:
        gap_ms = DEFAULT_AUDIO_GAP_MS
    validate_audio_gap_ms(gap_ms)

    # Combine audio files
    result = await combine_audio_files(
        clips_dir, f"{state['episode_name']}.mp3", audio_dir, gap_ms=gap_ms
    )

    final_path = Path(result["combined_audio_path"])
    logger.info(f"Combined audio saved to: {final_path}")

    return {"final_output_file_path": final_path}
