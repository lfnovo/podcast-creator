import json
from pathlib import Path
from typing import Dict, Optional, List, Union

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
from .episodes import load_episode_config
from .state import PodcastState

logger.info("Creating podcast generation graph")


def create_workflow_graph():
    """
    Create a LangGraph StateGraph for generating a podcast
    Defines nodes for each step of the podcast generation process

    Edges are defined to control the flow of the workflow.
    The graph is compiled into a callable LangGraph graph object.
    """
    # Define the graph
    workflow = StateGraph(PodcastState)
    logger.info("Generating workflow graph")

    # Add nodes
    workflow.add_node("generate_outline", generate_outline_node)
    workflow.add_node("generate_transcript", generate_transcript_node)
    workflow.add_node("generate_all_audio", generate_all_audio_node)
    workflow.add_node("combine_audio", combine_audio_node)

    # Define edges
    workflow.add_edge(START, "generate_outline")
    workflow.add_edge("generate_outline", "generate_transcript")

    workflow.add_conditional_edges(
        "generate_transcript", route_audio_generation, ["generate_all_audio", END]
    )
    workflow.add_edge("generate_all_audio", "combine_audio")
    workflow.add_edge("combine_audio", END)

    graph = workflow.compile()

    return graph
    


async def create_podcast(
    content: Union[str, List[str]],
    briefing: Optional[str] = None,
    episode_name: Optional[str] = None,
    output_dir: Optional[str] = None,
    speaker_config: Optional[str] = None,
    outline_provider: Optional[str] = None,
    outline_model: Optional[str] = None,
    transcript_provider: Optional[str] = None,
    transcript_model: Optional[str] = None,
    num_segments: Optional[int] = None,
    episode_profile: Optional[str] = None,
    briefing_suffix: Optional[str] = None,
    generate_audio: Optional[bool] = True,
) -> Dict:
    """
    High-level function to create a podcast using the LangGraph workflow

    Args:
        content: Source content for the podcast
        briefing: Podcast briefing/instructions (optional with episode_profile)
        episode_name: Name of the episode (required)
        output_dir: Output directory path (required)
        speaker_config: Speaker configuration name (optional with episode_profile)
        outline_provider: Provider for outline generation
        outline_model: Model for outline generation
        transcript_provider: Provider for transcript generation
        transcript_model: Model for transcript generation
        num_segments: Number of podcast segments
        episode_profile: Episode profile name to use for defaults
        briefing_suffix: Additional briefing text to append to profile default
        generate_audio: Whether to generate audio (optional, defaults to True)

    Returns:
        Dict with results including final audio path
    """
    # Resolve parameters using episode profile if provided
    if episode_profile:
        episode_config = load_episode_config(episode_profile)
        
        # Use episode profile defaults for missing parameters
        speaker_config = speaker_config or episode_config.speaker_config
        outline_provider = outline_provider or episode_config.outline_provider
        outline_model = outline_model or episode_config.outline_model
        transcript_provider = transcript_provider or episode_config.transcript_provider
        transcript_model = transcript_model or episode_config.transcript_model
        num_segments = num_segments or episode_config.num_segments
        generate_audio = generate_audio or episode_config.generate_audio

        # Resolve briefing with episode profile logic
        if briefing:
            # Explicit briefing overrides everything
            resolved_briefing = briefing
        elif briefing_suffix:
            # Combine default briefing with suffix
            resolved_briefing = f"{episode_config.default_briefing}\n\nAdditional focus: {briefing_suffix}"
        else:
            # Use default briefing from profile
            resolved_briefing = episode_config.default_briefing
    else:
        # Use provided parameters or defaults
        speaker_config = speaker_config or "ai_researchers"
        outline_provider = outline_provider or "openai"
        outline_model = outline_model or "gpt-4o-mini"
        transcript_provider = transcript_provider or "anthropic"
        transcript_model = transcript_model or "claude-3-5-sonnet-latest"
        num_segments = num_segments or 3
        resolved_briefing = briefing or ""
        generate_audio = generate_audio
    
    # Validate required parameters
    if not episode_name:
        raise ValueError("episode_name is required")
    if not output_dir:
        raise ValueError("output_dir is required")
    if not speaker_config:
        raise ValueError("speaker_config is required (either directly or via episode_profile)")
    if not resolved_briefing:
        raise ValueError("briefing is required (either directly, via episode_profile, or with briefing_suffix)")
    
    # Load speaker profile
    speaker_profile = load_speaker_config(speaker_config)

    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True, parents=True)

    # Create initial state
    initial_state = PodcastState(
        content=content,
        briefing=resolved_briefing,
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
            "generate_audio": generate_audio,
        }
    }

    # Create and run the graph
    graph = create_workflow_graph()
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
        "audio_clips_count": 0 if not generate_audio else len(result["audio_clips"]),
        "output_dir": output_path,
    }
