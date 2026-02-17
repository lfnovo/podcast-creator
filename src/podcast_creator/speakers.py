import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, field_validator


class Speaker(BaseModel):
    """Individual speaker profile"""

    name: str = Field(..., description="Speaker's name")
    voice_id: str = Field(..., description="Voice ID for TTS generation")
    backstory: str = Field(..., description="Speaker's background and expertise")
    personality: str = Field(
        ..., description="Speaker's personality traits and speaking style"
    )
    tts_provider: Optional[str] = Field(
        None, description="Override TTS provider for this speaker"
    )
    tts_model: Optional[str] = Field(
        None, description="Override TTS model for this speaker"
    )
    tts_config: Optional[Dict[str, Any]] = Field(
        None, description="Override TTS config for this speaker"
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError("Speaker name cannot be empty")
        return v.strip()


class SpeakerProfile(BaseModel):
    """Collection of speakers with shared TTS configuration"""

    tts_provider: str = Field(
        ..., description="TTS service provider (elevenlabs, openai, google)"
    )
    tts_model: str = Field(..., description="TTS model name")
    speakers: List[Speaker] = Field(..., description="List of speakers in this profile")
    tts_config: Optional[Dict[str, Any]] = Field(
        None, description="Config dict passed to AIFactory.create_text_to_speech()"
    )

    @field_validator("speakers")
    @classmethod
    def validate_speakers(cls, v):
        if len(v) < 1 or len(v) > 4:
            raise ValueError("Must have between 1 and 4 speakers")

        # Check for unique names
        names = [speaker.name for speaker in v]
        if len(names) != len(set(names)):
            raise ValueError("Speaker names must be unique")

        # Check for unique voice IDs
        voice_ids = [speaker.voice_id for speaker in v]
        if len(voice_ids) != len(set(voice_ids)):
            raise ValueError("Voice IDs must be unique")

        return v

    def get_speaker_names(self) -> List[str]:
        """Get list of speaker names"""
        return [speaker.name for speaker in self.speakers]

    def get_voice_mapping(self) -> Dict[str, str]:
        """Get mapping of speaker names to voice IDs"""
        return {speaker.name: speaker.voice_id for speaker in self.speakers}

    def get_speaker_by_name(self, name: str) -> Speaker:
        """Get speaker by name"""
        for speaker in self.speakers:
            if speaker.name == name:
                return speaker
        raise ValueError(f"Speaker '{name}' not found in profile")


class SpeakerConfig(BaseModel):
    """Configuration containing multiple speaker profiles"""

    profiles: Dict[str, SpeakerProfile] = Field(
        ..., description="Named speaker profiles"
    )

    @field_validator("profiles")
    @classmethod
    def validate_profiles(cls, v):
        if len(v) == 0:
            raise ValueError("At least one speaker profile must be defined")
        return v

    def get_profile(self, profile_name: str) -> SpeakerProfile:
        """Get speaker profile by name"""
        if profile_name not in self.profiles:
            raise ValueError(f"Speaker profile '{profile_name}' not found")
        return self.profiles[profile_name]

    def list_profiles(self) -> List[str]:
        """List available profile names"""
        return list(self.profiles.keys())

    @classmethod
    def load_from_file(cls, config_path: Union[Path, str]) -> "SpeakerConfig":
        """Load speaker configuration from JSON file"""
        if isinstance(config_path, str):
            config_path = Path(config_path)

        if not config_path.exists():
            raise FileNotFoundError(f"Speaker config file not found: {config_path}")

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return cls(**data)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in speaker config file: {e}")
        except Exception as e:
            raise ValueError(f"Error loading speaker config: {e}")


def load_speaker_config(config_name: str, project_root: Path = None) -> SpeakerProfile:
    """
    Load a specific speaker profile from configuration or file system.

    This function implements the priority cascade:
    1. Check configured speaker profiles
    2. Check configured speaker config file path
    3. Check current working directory for speakers_config.json
    4. Check bundled defaults

    Args:
        config_name: Name of the profile to load (e.g., "ai_researchers", "solo_expert")
        project_root: Project root directory (defaults to current working directory)

    Returns:
        SpeakerProfile: The loaded speaker profile
    """
    # Priority 1: Check configuration first
    try:
        from .config import ConfigurationManager
        config_manager = ConfigurationManager()
        configured_profile = config_manager.get_speaker_profile(config_name)
        if configured_profile:
            return configured_profile
    except Exception:
        pass  # Fall back to file-based loading

    # Priority 2: Check configured speaker config file path
    try:
        from .config import ConfigurationManager
        config_manager = ConfigurationManager()
        speakers_config_path = config_manager.get_config("speakers_config")
        
        if speakers_config_path and isinstance(speakers_config_path, str):
            config_path = Path(speakers_config_path)
            if config_path.exists():
                speaker_config = SpeakerConfig.load_from_file(config_path)
                
                # Use config_name directly as profile name
                return speaker_config.get_profile(config_name)
    except Exception:
        pass  # Fall back to default behavior

    # Priority 3: Use existing file-based loading (working directory)
    if project_root is None:
        project_root = Path.cwd()

    # Look for speakers_config.json in working directory
    config_path = project_root / "speakers_config.json"
    
    # Check if file exists in working directory
    if config_path.exists():
        speaker_config = SpeakerConfig.load_from_file(config_path)
        return speaker_config.get_profile(config_name)

    # Priority 4: Try bundled defaults
    try:
        import importlib.resources as resources
        
        # Try to load from package resources
        package_resources = resources.files("podcast_creator.resources")
        resource_file = package_resources / "speakers_config.json"
        
        if resource_file.is_file():
            content = resource_file.read_text()
            data = json.loads(content)
            speaker_config = SpeakerConfig(**data)
            return speaker_config.get_profile(config_name)
    except Exception:
        pass

    # If we get here, config not found
    raise ValueError(
        f"Speaker profile '{config_name}' not found. Please ensure it exists in one of:\n"
        f"1. Configured speakers via configure('speakers_config', {{...}})\n"
        f"2. Configured file path via configure('speakers_config', '/path/to/file.json')\n"
        f"3. ./speakers_config.json\n"
        f"4. Run 'podcast-creator init' to create default configuration"
    )
