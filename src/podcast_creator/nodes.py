import asyncio
import os
from pathlib import Path
from typing import Dict, List

from esperanto import AIFactory
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
from .retry import create_retry_decorator, get_retry_config
from .state import PodcastState

# Module-level TTS retry decorator (configured via env vars)
_tts_retry = create_retry_decorator(**get_retry_config())


async def generate_outline_node(state: PodcastState, config: RunnableConfig) -> Dict:
    """Generate podcast outline from content and briefing"""
    logger.info("Starting outline generation")

    configurable = config.get("configurable", {})
    outline_provider = configurable.get("outline_provider", "openai")
    outline_model_name = configurable.get("outline_model", "gpt-4o-mini")
    outline_config = configurable.get("outline_config") or {}

    # Create outline model
    merged_config = {
        "max_tokens": 3000,
        "structured": {"type": "json"},
        **outline_config,
    }
    outline_model = AIFactory.create_language(
        outline_provider,
        outline_model_name,
        config=merged_config,
    ).to_langchain()

    # Build retry decorator from configurable settings
    retry_cfg = get_retry_config(configurable)
    llm_retry = create_retry_decorator(**retry_cfg)

    @llm_retry
    async def _invoke_llm(prompt_text: str):
        return await outline_model.ainvoke(prompt_text)

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
        }
    )

    outline_preview = await _invoke_llm(outline_prompt_text)
    content = extract_text_content(outline_preview.content)
    content = clean_thinking_content(content)
    outline_result = outline_parser.invoke(content)

    logger.info(f"Generated outline with {len(outline_result.segments)} segments")

    return {"outline": outline_result}


async def generate_transcript_node(state: PodcastState, config: RunnableConfig) -> Dict:
    """Generate conversational transcript from outline"""
    logger.info("Starting transcript generation")

    assert state.get("outline") is not None, "outline must be provided"
    assert state.get("speaker_profile") is not None, "speaker_profile must be provided"

    configurable = config.get("configurable", {})
    transcript_provider: str = configurable.get("transcript_provider", "openai")
    transcript_model_name: str = configurable.get("transcript_model", "gpt-4o-mini")
    transcript_config = configurable.get("transcript_config") or {}

    # Create transcript model
    merged_config = {
        "max_tokens": 5000,
        "structured": {"type": "json"},
        **transcript_config,
    }
    transcript_model = AIFactory.create_language(
        transcript_provider,
        transcript_model_name,
        config=merged_config,
    ).to_langchain()

    # Create validated transcript parser
    speaker_profile = state["speaker_profile"]
    assert speaker_profile is not None, "speaker_profile must be provided"
    speaker_names = speaker_profile.get_speaker_names()
    validated_transcript_parser = create_validated_transcript_parser(speaker_names)

    # Build retry decorator from configurable settings
    retry_cfg = get_retry_config(configurable)
    llm_retry = create_retry_decorator(**retry_cfg)

    @llm_retry
    async def _invoke_llm(prompt_text: str):
        return await transcript_model.ainvoke(prompt_text)

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
        }

        transcript_prompt = get_transcript_prompter()
        transcript_prompt_rendered = transcript_prompt.render(data)
        transcript_preview = await _invoke_llm(transcript_prompt_rendered)
        content = extract_text_content(transcript_preview.content)
        content = clean_thinking_content(content)
        result = validated_transcript_parser.invoke(content)
        transcript.extend(result.transcript)

    logger.info(f"Generated transcript with {len(transcript)} dialogue segments")

    return {"transcript": transcript}


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
            task = generate_single_audio_clip(dialogue_info)
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


@_tts_retry
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

    # Combine audio files
    result = await combine_audio_files(
        clips_dir, f"{state['episode_name']}.mp3", audio_dir
    )

    final_path = Path(result["combined_audio_path"])
    logger.info(f"Combined audio saved to: {final_path}")

    return {"final_output_file_path": final_path}
