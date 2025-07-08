import json
from pathlib import Path
from typing import Dict, Union

from pydantic import BaseModel, Field, field_validator


class EpisodeProfile(BaseModel):
    """Individual episode profile configuration"""

    speaker_config: str = Field(..., description="Speaker configuration name")
    outline_provider: str = Field(
        "openai", description="Provider for outline generation"
    )
    outline_model: str = Field("gpt-4o-mini", description="Model for outline generation")
    transcript_provider: str = Field(
        "anthropic", description="Provider for transcript generation"
    )
    transcript_model: str = Field(
        "claude-3-5-sonnet-latest", description="Model for transcript generation"
    )
    default_briefing: str = Field(
        "", description="Default briefing for this episode type"
    )
    num_segments: int = Field(3, description="Number of podcast segments")

    @field_validator("speaker_config")
    @classmethod
    def validate_speaker_config(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError("Speaker config cannot be empty")
        return v.strip()

    @field_validator("num_segments")
    @classmethod
    def validate_num_segments(cls, v):
        if v < 1 or v > 10:
            raise ValueError("Number of segments must be between 1 and 10")
        return v

    @field_validator("outline_provider", "transcript_provider")
    @classmethod
    def validate_providers(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError("Provider cannot be empty")
        return v.strip()

    @field_validator("outline_model", "transcript_model")
    @classmethod
    def validate_models(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError("Model cannot be empty")
        return v.strip()


class EpisodeConfig(BaseModel):
    """Configuration containing multiple episode profiles"""

    profiles: Dict[str, EpisodeProfile] = Field(
        ..., description="Named episode profiles"
    )

    @field_validator("profiles")
    @classmethod
    def validate_profiles(cls, v):
        if len(v) == 0:
            raise ValueError("At least one episode profile must be defined")
        return v

    def get_profile(self, profile_name: str) -> EpisodeProfile:
        """Get episode profile by name"""
        if profile_name not in self.profiles:
            raise ValueError(f"Episode profile '{profile_name}' not found")
        return self.profiles[profile_name]

    def list_profiles(self) -> list[str]:
        """List available profile names"""
        return list(self.profiles.keys())

    @classmethod
    def load_from_file(cls, config_path: Union[Path, str]) -> "EpisodeConfig":
        """Load episode configuration from JSON file"""
        if isinstance(config_path, str):
            config_path = Path(config_path)

        if not config_path.exists():
            raise FileNotFoundError(f"Episode config file not found: {config_path}")

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return cls(**data)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in episode config file: {e}")
        except Exception as e:
            raise ValueError(f"Error loading episode config: {e}")


def load_episode_config(config_name: str, project_root: Path = None) -> EpisodeProfile:
    """
    Load a specific episode profile from configuration or file system.

    This function implements the priority cascade:
    1. Check configured episode profiles
    2. Check configured episode config file path
    3. Check current working directory for episodes_config.json
    4. Check bundled defaults

    Args:
        config_name: Name of the profile to load (e.g., "tech_discussion", "solo_expert")
        project_root: Project root directory (defaults to current working directory)

    Returns:
        EpisodeProfile: The loaded episode profile
    """
    # Priority 1: Check configuration first
    try:
        from .config import ConfigurationManager
        config_manager = ConfigurationManager()
        configured_profile = config_manager.get_episode_profile(config_name)
        if configured_profile:
            return configured_profile
    except Exception:
        pass  # Fall back to file-based loading

    # Priority 2: Check configured episode config file path
    try:
        from .config import ConfigurationManager
        config_manager = ConfigurationManager()
        episodes_config_path = config_manager.get_config("episode_config")
        
        if episodes_config_path and isinstance(episodes_config_path, str):
            config_path = Path(episodes_config_path)
            if config_path.exists():
                episode_config = EpisodeConfig.load_from_file(config_path)
                return episode_config.get_profile(config_name)
    except Exception:
        pass  # Fall back to default behavior

    # Priority 3: Use existing file-based loading (working directory)
    if project_root is None:
        project_root = Path.cwd()

    # Look for episodes_config.json in working directory
    config_path = project_root / "episodes_config.json"
    
    # Check if file exists in working directory
    if config_path.exists():
        episode_config = EpisodeConfig.load_from_file(config_path)
        return episode_config.get_profile(config_name)

    # Priority 4: Try bundled defaults
    try:
        import importlib.resources as resources
        
        # Try to load from package resources
        package_resources = resources.files("podcast_creator.resources")
        resource_file = package_resources / "episodes_config.json"
        
        if resource_file.is_file():
            content = resource_file.read_text()
            data = json.loads(content)
            episode_config = EpisodeConfig(**data)
            return episode_config.get_profile(config_name)
    except Exception:
        pass

    # If we get here, config not found
    raise ValueError(
        f"Episode profile '{config_name}' not found. Please ensure it exists in one of:\n"
        f"1. Configured episodes via configure('episode_config', {{...}})\n"
        f"2. Configured file path via configure('episode_config', '/path/to/file.json')\n"
        f"3. ./episodes_config.json\n"
        f"4. Run 'podcast-creator init' to create default configuration"
    )