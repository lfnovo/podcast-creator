from operator import add
from pathlib import Path
from typing import Annotated, List, Optional, TypedDict, Union, Dict

from .core import Dialogue, Outline
from .speakers import SpeakerProfile


class PodcastState(TypedDict):
    # Input data
    content: Union[str, List[Dict]]
    briefing: str
    num_segments: int

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
