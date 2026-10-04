from operator import add
from pathlib import Path
from typing import Annotated, List, Optional, TypedDict, Union

from .core import Dialogue, Outline
from .speakers import SpeakerProfile


class PodcastState(TypedDict):
    # Input data
    content: Union[str, List[str]]
    briefing: str
    num_segments: int
    language: Optional[str]

    # Generated content
    outline: Optional[Outline]
    transcript: List[Dialogue]

    # Audio processing
    audio_clips: Annotated[List[Path], add]
    final_output_file_path: Optional[Path]

    # Configuration
    output_dir: Path
    episode_name: str
    speaker_profile: Optional[SpeakerProfile]

    # "provider/model" keys that rejected json_schema and use generic JSON for the run
    json_mode_models: List[str]
