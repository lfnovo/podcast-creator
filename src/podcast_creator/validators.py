"""Validation utilities for podcast-creator package."""

import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from jinja2 import Template, TemplateSyntaxError
from loguru import logger

from .speakers import SpeakerConfig


def validate_template_syntax(template_content: str, template_name: str = "template") -> bool:
    """
    Validate Jinja2 template syntax.

    Args:
        template_content: Template content to validate
        template_name: Name of the template for error messages

    Returns:
        True if template syntax is valid

    Raises:
        ValueError: If template syntax is invalid
    """
    try:
        Template(template_content)
        return True
    except TemplateSyntaxError as e:
        raise ValueError(
            f"Invalid template syntax in {template_name} at line {e.lineno}: {e.message}"
        )
    except Exception as e:
        raise ValueError(f"Error validating template {template_name}: {e}")


def validate_template_variables(
    template_content: str, required_vars: List[str], template_name: str = "template"
) -> bool:
    """
    Validate that a template contains required variables.

    Args:
        template_content: Template content to validate
        required_vars: List of required variable names
        template_name: Name of the template for error messages

    Returns:
        True if all required variables are present

    Raises:
        ValueError: If required variables are missing
    """
    # Extract variable names from template
    variable_pattern = r"{{\s*(\w+)(?:\s*\|.*?)?\s*}}"
    found_vars = set(re.findall(variable_pattern, template_content))

    missing_vars = set(required_vars) - found_vars
    if missing_vars:
        raise ValueError(
            f"Template {template_name} is missing required variables: {', '.join(missing_vars)}"
        )

    return True


def validate_speaker_config_schema(config: Dict[str, Any]) -> bool:
    """
    Validate speaker configuration schema.

    Args:
        config: Speaker configuration dictionary

    Returns:
        True if configuration is valid

    Raises:
        ValueError: If configuration is invalid
    """
    try:
        SpeakerConfig(**config)
        return True
    except Exception as e:
        raise ValueError(f"Invalid speaker configuration: {e}")


def validate_file_path(path: str, must_exist: bool = True, must_be_file: bool = True) -> bool:
    """
    Validate file path.

    Args:
        path: File path to validate
        must_exist: Whether file must exist
        must_be_file: Whether path must be a file (not directory)

    Returns:
        True if path is valid

    Raises:
        ValueError: If path validation fails
    """
    file_path = Path(path)

    if must_exist and not file_path.exists():
        raise ValueError(f"File does not exist: {path}")

    if must_exist and must_be_file and not file_path.is_file():
        raise ValueError(f"Path is not a file: {path}")

    return True


def validate_directory_path(path: str, must_exist: bool = True) -> bool:
    """
    Validate directory path.

    Args:
        path: Directory path to validate
        must_exist: Whether directory must exist

    Returns:
        True if path is valid

    Raises:
        ValueError: If path validation fails
    """
    dir_path = Path(path)

    if must_exist and not dir_path.exists():
        raise ValueError(f"Directory does not exist: {path}")

    if must_exist and not dir_path.is_dir():
        raise ValueError(f"Path is not a directory: {path}")

    return True


def validate_outline_template(template_content: str) -> bool:
    """
    Validate outline template specifically.

    Args:
        template_content: Template content

    Returns:
        True if template is valid

    Raises:
        ValueError: If template is invalid
    """
    # Check syntax
    validate_template_syntax(template_content, "outline template")

    # Check required variables for outline generation
    required_vars = ["briefing", "num_segments", "context"]
    validate_template_variables(template_content, required_vars, "outline template")

    logger.debug("Outline template validation passed")
    return True


def validate_transcript_template(template_content: str) -> bool:
    """
    Validate transcript template specifically.

    Args:
        template_content: Template content

    Returns:
        True if template is valid

    Raises:
        ValueError: If template is invalid
    """
    # Check syntax
    validate_template_syntax(template_content, "transcript template")

    # Check required variables for transcript generation
    required_vars = ["briefing", "context", "segment", "speakers"]
    validate_template_variables(template_content, required_vars, "transcript template")

    logger.debug("Transcript template validation passed")
    return True


def validate_voice_ids(speaker_config: Dict[str, Any], provider: str) -> bool:
    """
    Validate voice IDs for specific TTS provider.

    Args:
        speaker_config: Speaker configuration
        provider: TTS provider name

    Returns:
        True if voice IDs are valid format

    Raises:
        ValueError: If voice IDs are invalid
    """
    try:
        config = SpeakerConfig(**speaker_config)
        
        for profile_name, profile in config.profiles.items():
            if profile.tts_provider.lower() != provider.lower():
                continue
                
            for speaker in profile.speakers:
                voice_id = speaker.voice_id
                
                # Basic validation - voice IDs should not be empty
                if not voice_id or not voice_id.strip():
                    raise ValueError(
                        f"Empty voice_id for speaker '{speaker.name}' in profile '{profile_name}'"
                    )
                
                # Provider-specific validation could be added here
                if provider.lower() == "elevenlabs":
                    # ElevenLabs voice IDs are typically alphanumeric strings
                    if not re.match(r"^[a-zA-Z0-9_-]+$", voice_id):
                        logger.warning(
                            f"Voice ID '{voice_id}' for speaker '{speaker.name}' "
                            f"may not be valid for ElevenLabs"
                        )
                
        return True
        
    except Exception as e:
        raise ValueError(f"Error validating voice IDs: {e}")


def validate_configuration_completeness(config: Dict[str, Any]) -> bool:
    """
    Validate that configuration is complete for podcast generation.

    Args:
        config: Complete configuration dictionary

    Returns:
        True if configuration is complete

    Raises:
        ValueError: If configuration is incomplete
    """
    issues = []

    # Check for either templates or prompts_dir
    has_templates = "templates" in config and config["templates"] is not None
    has_prompts_dir = "prompts_dir" in config and config["prompts_dir"] is not None
    
    if not has_templates and not has_prompts_dir:
        # Check if templates exist in current directory
        cwd_outline = Path.cwd() / "prompts" / "podcast" / "outline.jinja"
        cwd_transcript = Path.cwd() / "prompts" / "podcast" / "transcript.jinja"
        
        if not (cwd_outline.exists() and cwd_transcript.exists()):
            issues.append(
                "No templates configured. Please set 'templates' or 'prompts_dir', "
                "or run 'podcast-creator init'"
            )

    # Check for speaker configuration
    has_speakers = "speakers_config" in config and config["speakers_config"] is not None
    
    if not has_speakers:
        # Check if speakers_config.json exists in current directory
        cwd_speakers = Path.cwd() / "speakers_config.json"
        
        if not cwd_speakers.exists():
            issues.append(
                "No speaker configuration found. Please set 'speakers_config' "
                "or run 'podcast-creator init'"
            )

    if issues:
        raise ValueError(
            "Configuration incomplete:\n" + "\n".join(f"- {issue}" for issue in issues)
        )

    logger.debug("Configuration completeness validation passed")
    return True