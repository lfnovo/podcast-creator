"""
Podcast Creator - AI-powered podcast generation tool.

This package provides tools for creating conversational audio content from text sources.
"""

from .config import PodcastConfig, configure, get_config
from .core import (
    Dialogue,
    Outline,
    Segment,
    Transcript,
    clean_thinking_content,
    combine_audio_files,
    parse_thinking_content,
)
from .graph import PodcastState, create_podcast
from .graph import graph as podcast_graph
from .speakers import Speaker, SpeakerConfig, SpeakerProfile, load_speaker_config

try:
    import importlib.metadata as metadata
except ImportError:
    # Python < 3.8 fallback
    import importlib_metadata as metadata

try:
    __version__ = metadata.version("podcast-creator")
except Exception:
    # Fallback for development/editable installs
    __version__ = "0.1.0-dev"
__all__ = [
    # Configuration
    "configure",
    "get_config",
    "PodcastConfig",
    # Core functions (kept for utilities)
    "combine_audio_files",
    "parse_thinking_content",
    "clean_thinking_content",
    # Data models
    "Segment",
    "Outline",
    "Dialogue",
    "Transcript",
    # LangGraph functions
    "create_podcast",
    "podcast_graph",
    "PodcastState",
    # Speaker models
    "Speaker",
    "SpeakerProfile",
    "SpeakerConfig",
    "load_speaker_config",
]
