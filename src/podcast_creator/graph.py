import json
from pathlib import Path
from typing import Dict

from langgraph.graph import END, START, StateGraph
from loguru import logger

from .nodes import (
    combine_audio_node,
    generate_all_audio_node,
    generate_outline_node,
    generate_transcript_node,
    route_audio_generation,
)
from .speakers import load_speaker_config
from .state import PodcastState

logger.info("Creating podcast generation graph")

# Define the graph
workflow = StateGraph(PodcastState)

# Add nodes
workflow.add_node("generate_outline", generate_outline_node)
workflow.add_node("generate_transcript", generate_transcript_node)
workflow.add_node("generate_all_audio", generate_all_audio_node)
workflow.add_node("combine_audio", combine_audio_node)

# Define edges
workflow.add_edge(START, "generate_outline")
workflow.add_edge("generate_outline", "generate_transcript")
workflow.add_conditional_edges(
    "generate_transcript", route_audio_generation, ["generate_all_audio"]
)
workflow.add_edge("generate_all_audio", "combine_audio")
workflow.add_edge("combine_audio", END)

graph = workflow.compile()


async def create_podcast(
    content: str,
    briefing: str,
    episode_name: str,
    output_dir: str,
    speaker_config: str,
    outline_provider: str = "openai",
    outline_model: str = "gpt-4o-mini",
    transcript_provider: str = "anthropic",
    transcript_model: str = "claude-3-5-sonnet-latest",
    num_segments: int = 3,
) -> Dict:
    """
    High-level function to create a podcast using the LangGraph workflow

    Args:
        content: Source content for the podcast
        briefing: Podcast briefing/instructions
        episode_name: Name of the episode
        output_dir: Output directory path
        speaker_config: Speaker configuration name (format: "filename:profile_name")
        outline_provider: Provider for outline generation
        outline_model: Model for outline generation
        transcript_provider: Provider for transcript generation
        transcript_model: Model for transcript generation
        num_segments: Number of podcast segments

    Returns:
        Dict with results including final audio path
    """
    # Load speaker profile
    speaker_profile = load_speaker_config(speaker_config)

    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True, parents=True)

    # Create initial state
    initial_state = PodcastState(
        content=content,
        briefing=briefing,
        num_segments=num_segments,
        outline=None,
        transcript=[],
        audio_clips=[],
        final_output_file_path=None,
        output_dir=output_path,
        episode_name=episode_name,
        speaker_profile=speaker_profile,
    )

    # Create configuration
    config = {
        "configurable": {
            "outline_provider": outline_provider,
            "outline_model": outline_model,
            "transcript_provider": transcript_provider,
            "transcript_model": transcript_model,
        }
    }

    # Create and run the graph
    result = await graph.ainvoke(initial_state, config=config)

    # Save outputs
    if result["outline"]:
        outline_path = output_path / "outline.json"
        outline_path.write_text(result["outline"].model_dump_json())

    if result["transcript"]:
        transcript_path = output_path / "transcript.json"
        transcript_path.write_text(
            json.dumps([d.model_dump() for d in result["transcript"]], indent=2)
        )

    return {
        "outline": result["outline"],
        "transcript": result["transcript"],
        "final_output_file_path": result["final_output_file_path"],
        "audio_clips_count": len(result["audio_clips"]),
        "output_dir": output_path,
    }
