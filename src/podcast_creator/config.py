"""Configuration management for podcast-creator package."""

from pathlib import Path
from typing import Any, Dict, Optional, Union

from ai_prompter import Prompter
from langchain_core.output_parsers.pydantic import PydanticOutputParser
from loguru import logger
from pydantic import BaseModel, Field, validator

from .speakers import SpeakerConfig, SpeakerProfile
from .episodes import EpisodeConfig, EpisodeProfile


class TemplateConfig(BaseModel):
    """Configuration for prompt templates."""

    outline: Optional[str] = Field(None, description="Outline template content")
    transcript: Optional[str] = Field(None, description="Transcript template content")

    @validator("outline", "transcript")
    def validate_template(cls, v: Optional[str]) -> Optional[str]:
        """Validate template is not empty if provided."""
        if v is not None and not v.strip():
            raise ValueError("Template content cannot be empty")
        return v


class PodcastConfig(BaseModel):
    """Configuration for podcast creator."""

    prompts_dir: Optional[str] = Field(
        None, description="Directory containing prompt templates"
    )
    speakers_config: Optional[Union[str, Dict[str, Any]]] = Field(
        None, description="Path to speakers config JSON or inline config dict"
    )
    output_dir: Optional[str] = Field(
        None, description="Default output directory for generated podcasts"
    )
    templates: Optional[TemplateConfig] = Field(
        None, description="Inline template configurations"
    )
    episode_config: Optional[Union[str, Dict[str, Any]]] = Field(
        None, description="Path to episode config JSON or inline config dict"
    )

    @validator("prompts_dir")
    def validate_prompts_dir(cls, v: Optional[str]) -> Optional[str]:
        """Validate prompts directory if provided."""
        if v is not None:
            path = Path(v)
            if path.exists() and not path.is_dir():
                raise ValueError(f"Prompts path is not a directory: {v}")
        return v
    
    @validator("output_dir")
    def validate_output_dir(cls, v: Optional[str]) -> Optional[str]:
        """Validate output directory (can be created if doesn't exist)."""
        # Output dir doesn't need to exist - it can be created
        return v

    @validator("speakers_config")
    def validate_speakers_config(
        cls, v: Optional[Union[str, Dict[str, Any]]]
    ) -> Optional[Union[str, Dict[str, Any]]]:
        """Validate speakers configuration."""
        if v is None:
            return v

        if isinstance(v, str):
            # Validate file path
            path = Path(v)
            if not path.exists():
                raise ValueError(f"Speakers config file not found: {v}")
            if not path.suffix == ".json":
                raise ValueError(f"Speakers config must be a JSON file: {v}")
        elif isinstance(v, dict):
            # Validate dictionary structure
            try:
                SpeakerConfig(**v)
            except Exception as e:
                raise ValueError(f"Invalid speakers config structure: {e}")

        return v

    @validator("episode_config")
    def validate_episode_config(
        cls, v: Optional[Union[str, Dict[str, Any]]]
    ) -> Optional[Union[str, Dict[str, Any]]]:
        """Validate episode configuration."""
        if v is None:
            return v

        if isinstance(v, str):
            # Validate file path
            path = Path(v)
            if not path.exists():
                raise ValueError(f"Episode config file not found: {v}")
            if not path.suffix == ".json":
                raise ValueError(f"Episode config must be a JSON file: {v}")
        elif isinstance(v, dict):
            # Validate dictionary structure
            try:
                EpisodeConfig(**v)
            except Exception as e:
                raise ValueError(f"Invalid episode config structure: {e}")

        return v


class ConfigurationManager:
    """Central configuration management for podcast-creator."""

    _instance = None
    _config: Dict[str, Any] = {}

    def __new__(cls):
        """Implement singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._config = {}
        return cls._instance

    def configure(
        self, key_or_dict: Union[str, Dict[str, Any]], value: Any = None
    ) -> None:
        """
        Configure podcast creator settings.

        Args:
            key_or_dict: Configuration key or dictionary of settings
            value: Configuration value (if key_or_dict is a string)

        Examples:
            # Configure single setting
            configure("prompts_dir", "/path/to/prompts")

            # Configure multiple settings
            configure({
                "prompts_dir": "/path/to/prompts",
                "speakers_config": "/path/to/speakers.json"
            })

            # Configure inline templates
            configure("templates", {
                "outline": "template content...",
                "transcript": "template content..."
            })
        """
        if isinstance(key_or_dict, dict):
            # Validate entire config
            updates = key_or_dict
        else:
            # Single key-value update
            updates = {key_or_dict: value}

        # Special handling for nested configs
        for key, val in updates.items():
            if key == "templates" and isinstance(val, dict):
                # Convert to TemplateConfig for validation
                updates[key] = TemplateConfig(**val)
            elif key == "speakers_config" and isinstance(val, dict):
                # Validate speaker config structure
                SpeakerConfig(**val)
            elif key == "episode_config" and isinstance(val, dict):
                # Validate episode config structure
                EpisodeConfig(**val)

        # Validate updates fit our schema
        current = self._config.copy()
        current.update(updates)
        PodcastConfig(**current)  # This will raise if invalid

        # Apply updates
        self._config.update(updates)
        logger.debug(f"Configuration updated: {list(updates.keys())}")

    def get_config(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value.

        Args:
            key: Configuration key
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        return self._config.get(key, default)

    def get_template_prompter(
        self, template_name: str, parser: Optional[PydanticOutputParser] = None
    ) -> Prompter:
        """
        Get a Prompter instance for the specified template.

        This method implements the priority cascade:
        1. User-configured template strings
        2. User-configured prompts directory
        3. Current working directory
        4. Bundled defaults

        Args:
            template_name: Name of the template ("outline" or "transcript")
            parser: Optional parser for the prompter

        Returns:
            Configured Prompter instance

        Raises:
            ValueError: If template cannot be found
        """
        # Priority 1: Check inline templates
        templates = self.get_config("templates")
        if templates and hasattr(templates, template_name):
            template_content = getattr(templates, template_name)
            if template_content:
                logger.debug(
                    f"Using configured template string for '{template_name}'"
                )
                return Prompter(
                    template_text=template_content,
                    parser=parser,
                )

        # Priority 2: Check configured prompts directory
        prompts_dir = self.get_config("prompts_dir")
        if prompts_dir:
            template_path = Path(prompts_dir) / "podcast" / f"{template_name}.jinja"
            if template_path.exists():
                logger.debug(
                    f"Using template from configured directory: {template_path}"
                )
                return Prompter(
                    prompt_template=f"podcast/{template_name}.jinja",
                    parser=parser,
                    prompt_dir=prompts_dir,
                )

        # Priority 3: Check current working directory
        cwd_template_path = Path.cwd() / "prompts" / "podcast" / f"{template_name}.jinja"
        if cwd_template_path.exists():
            logger.debug(f"Using template from current directory: {cwd_template_path}")
            return Prompter(
                prompt_template=f"podcast/{template_name}.jinja",
                parser=parser,
            )

        # Priority 4: Use bundled defaults
        try:
            import importlib.resources as resources

            # Try to load from package resources
            package_resources = resources.files("podcast_creator.resources")
            template_resource = (
                package_resources / "prompts" / "podcast" / f"{template_name}.jinja"
            )

            if template_resource.is_file():
                template_content = template_resource.read_text()
                logger.debug(f"Using bundled template for '{template_name}'")
                return Prompter(
                    template_text=template_content,
                    parser=parser,
                )
        except Exception as e:
            logger.debug(f"Could not load bundled template: {e}")

        # If we get here, template not found
        raise ValueError(
            f"Template '{template_name}' not found. Please ensure it exists in one of:\n"
            f"1. Configured templates via configure('templates', {{...}})\n"
            f"2. Configured prompts directory via configure('prompts_dir', '/path')\n"
            f"3. ./prompts/podcast/{template_name}.jinja\n"
            f"4. Run 'podcast-creator init' to create default templates"
        )

    def get_speaker_profile(self, config_name: str) -> Optional[SpeakerProfile]:
        """
        Get speaker profile from configuration.

        Args:
            config_name: Name of the speaker profile

        Returns:
            SpeakerProfile if found in configuration, None otherwise
        """
        speakers_config = self.get_config("speakers_config")
        if not speakers_config:
            return None

        if isinstance(speakers_config, dict):
            # Inline speaker configuration
            try:
                speaker_config = SpeakerConfig(**speakers_config)
                # Use config_name directly as profile name
                if config_name in speaker_config.profiles:
                    logger.debug(
                        f"Using configured speaker profile: {config_name}"
                    )
                    return speaker_config.get_profile(config_name)
            except Exception as e:
                logger.debug(f"Could not load speaker profile from config: {e}")

        return None

    def get_episode_profile(self, config_name: str) -> Optional[EpisodeProfile]:
        """
        Get episode profile from configuration.

        Args:
            config_name: Name of the episode profile

        Returns:
            EpisodeProfile if found in configuration, None otherwise
        """
        episode_config = self.get_config("episode_config")
        if not episode_config:
            return None

        if isinstance(episode_config, dict):
            # Inline episode configuration
            try:
                episode_config_obj = EpisodeConfig(**episode_config)
                # Use config_name directly as profile name
                if config_name in episode_config_obj.profiles:
                    logger.debug(
                        f"Using configured episode profile: {config_name}"
                    )
                    return episode_config_obj.get_profile(config_name)
            except Exception as e:
                logger.debug(f"Could not load episode profile from config: {e}")

        return None


# Module-level convenience functions
_manager = ConfigurationManager()


def configure(key_or_dict: Union[str, Dict[str, Any]], value: Any = None) -> None:
    """
    Configure podcast creator settings.

    Args:
        key_or_dict: Configuration key or dictionary of settings
        value: Configuration value (if key_or_dict is a string)

    Examples:
        # Configure single setting
        configure("prompts_dir", "/path/to/prompts")

        # Configure multiple settings
        configure({
            "prompts_dir": "/path/to/prompts",
            "speakers_config": "/path/to/speakers.json"
        })
    """
    _manager.configure(key_or_dict, value)


def get_config(key: str, default: Any = None) -> Any:
    """
    Get configuration value.

    Args:
        key: Configuration key
        default: Default value if key not found

    Returns:
        Configuration value or default
    """
    return _manager.get_config(key, default)