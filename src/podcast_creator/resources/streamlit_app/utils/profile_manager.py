"""
Profile management utilities for the Podcast Creator Studio.

Handles CRUD operations for speaker and episode profiles.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
import streamlit as st
from copy import deepcopy

try:
    from podcast_creator import load_speaker_config, load_episode_config, configure  # noqa: F401
    PODCAST_CREATOR_AVAILABLE = True
except ImportError:
    PODCAST_CREATOR_AVAILABLE = False


class ProfileManager:
    """Manages speaker and episode profiles including CRUD operations."""
    
    def __init__(self, working_dir: str = "."):
        """
        Initialize the profile manager.
        
        Args:
            working_dir: Working directory for profile files
        """
        self.working_dir = Path(working_dir)
        self.speakers_config_path = self.working_dir / "speakers_config.json"
        self.episodes_config_path = self.working_dir / "episodes_config.json"
        
        # Initialize config files if they don't exist
        self._ensure_config_files()
    
    def _ensure_config_files(self):
        """Ensure configuration files exist with default structure."""
        
        # Default speaker config structure
        default_speakers = {
            "profiles": {
                "ai_researchers": {
                    "tts_provider": "elevenlabs",
                    "tts_model": "eleven_flash_v2_5",
                    "speakers": [
                        {
                            "name": "Dr. Alex Chen",
                            "voice_id": "voice_id_1",
                            "backstory": "Senior AI researcher with focus on machine learning ethics",
                            "personality": "Thoughtful, asks probing questions, explains complex concepts clearly"
                        },
                        {
                            "name": "Jamie Rodriguez",
                            "voice_id": "voice_id_2", 
                            "backstory": "Tech journalist and startup advisor with 10 years experience",
                            "personality": "Enthusiastic, great at explanations, bridges technical and business perspectives"
                        }
                    ]
                },
                "solo_expert": {
                    "tts_provider": "elevenlabs",
                    "tts_model": "eleven_flash_v2_5",
                    "speakers": [
                        {
                            "name": "Dr. Sarah Mitchell",
                            "voice_id": "voice_id_3",
                            "backstory": "Expert educator and researcher with ability to explain complex topics",
                            "personality": "Clear, authoritative, engaging, uses analogies and examples"
                        }
                    ]
                }
            }
        }
        
        # Default episode config structure
        default_episodes = {
            "profiles": {
                "tech_discussion": {
                    "speaker_config": "ai_researchers",
                    "outline_model": "gpt-4o",
                    "transcript_model": "gpt-4o",
                    "num_segments": 4,
                    "default_briefing": "Create an engaging technical discussion that explores the topic in depth"
                },
                "solo_expert": {
                    "speaker_config": "solo_expert",
                    "outline_model": "gpt-4o", 
                    "transcript_model": "gpt-4o",
                    "num_segments": 3,
                    "default_briefing": "Create an educational explanation that breaks down complex concepts"
                }
            }
        }
        
        # Create speakers config if it doesn't exist
        if not self.speakers_config_path.exists():
            self._save_json(self.speakers_config_path, default_speakers)
        
        # Create episodes config if it doesn't exist
        if not self.episodes_config_path.exists():
            self._save_json(self.episodes_config_path, default_episodes)
    
    def _load_json(self, file_path: Path) -> Dict[str, Any]:
        """Load JSON data from file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            st.error(f"Error loading {file_path}: {e}")
            return {}
    
    def _save_json(self, file_path: Path, data: Dict[str, Any]) -> bool:
        """Save JSON data to file."""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            st.error(f"Error saving {file_path}: {e}")
            return False
    
    # Speaker Profile Management
    
    def load_speaker_profiles(self) -> Dict[str, Any]:
        """Load all speaker profiles."""
        return self._load_json(self.speakers_config_path)
    
    def get_speaker_profile(self, profile_name: str) -> Optional[Dict[str, Any]]:
        """Get a specific speaker profile."""
        profiles = self.load_speaker_profiles()
        return profiles.get("profiles", {}).get(profile_name)
    
    def create_speaker_profile(self, profile_name: str, profile_data: Dict[str, Any]) -> bool:
        """Create a new speaker profile."""
        profiles = self.load_speaker_profiles()
        
        if profile_name in profiles.get("profiles", {}):
            st.error(f"Speaker profile '{profile_name}' already exists")
            return False
        
        profiles.setdefault("profiles", {})[profile_name] = profile_data
        return self._save_json(self.speakers_config_path, profiles)
    
    def update_speaker_profile(self, profile_name: str, profile_data: Dict[str, Any]) -> bool:
        """Update an existing speaker profile."""
        profiles = self.load_speaker_profiles()
        
        if profile_name not in profiles.get("profiles", {}):
            st.error(f"Speaker profile '{profile_name}' not found")
            return False
        
        profiles["profiles"][profile_name] = profile_data
        return self._save_json(self.speakers_config_path, profiles)
    
    def delete_speaker_profile(self, profile_name: str) -> bool:
        """Delete a speaker profile."""
        profiles = self.load_speaker_profiles()
        
        if profile_name not in profiles.get("profiles", {}):
            st.error(f"Speaker profile '{profile_name}' not found")
            return False
        
        del profiles["profiles"][profile_name]
        return self._save_json(self.speakers_config_path, profiles)
    
    def clone_speaker_profile(self, source_name: str, new_name: str) -> bool:
        """Clone a speaker profile with a new name."""
        source_profile = self.get_speaker_profile(source_name)
        
        if not source_profile:
            st.error(f"Source speaker profile '{source_name}' not found")
            return False
        
        cloned_profile = deepcopy(source_profile)
        return self.create_speaker_profile(new_name, cloned_profile)
    
    def get_speaker_profile_names(self) -> List[str]:
        """Get list of all speaker profile names."""
        profiles = self.load_speaker_profiles()
        return list(profiles.get("profiles", {}).keys())
    
    # Episode Profile Management
    
    def load_episode_profiles(self) -> Dict[str, Any]:
        """Load all episode profiles."""
        return self._load_json(self.episodes_config_path)
    
    def get_episode_profile(self, profile_name: str) -> Optional[Dict[str, Any]]:
        """Get a specific episode profile."""
        profiles = self.load_episode_profiles()
        return profiles.get("profiles", {}).get(profile_name)
    
    def create_episode_profile(self, profile_name: str, profile_data: Dict[str, Any]) -> bool:
        """Create a new episode profile."""
        profiles = self.load_episode_profiles()
        
        if profile_name in profiles.get("profiles", {}):
            st.error(f"Episode profile '{profile_name}' already exists")
            return False
        
        profiles.setdefault("profiles", {})[profile_name] = profile_data
        return self._save_json(self.episodes_config_path, profiles)
    
    def update_episode_profile(self, profile_name: str, profile_data: Dict[str, Any]) -> bool:
        """Update an existing episode profile."""
        profiles = self.load_episode_profiles()
        
        if profile_name not in profiles.get("profiles", {}):
            st.error(f"Episode profile '{profile_name}' not found")
            return False
        
        profiles["profiles"][profile_name] = profile_data
        return self._save_json(self.episodes_config_path, profiles)
    
    def delete_episode_profile(self, profile_name: str) -> bool:
        """Delete an episode profile."""
        profiles = self.load_episode_profiles()
        
        if profile_name not in profiles.get("profiles", {}):
            st.error(f"Episode profile '{profile_name}' not found")
            return False
        
        del profiles["profiles"][profile_name]
        return self._save_json(self.episodes_config_path, profiles)
    
    def clone_episode_profile(self, source_name: str, new_name: str) -> bool:
        """Clone an episode profile with a new name."""
        source_profile = self.get_episode_profile(source_name)
        
        if not source_profile:
            st.error(f"Source episode profile '{source_name}' not found")
            return False
        
        cloned_profile = deepcopy(source_profile)
        return self.create_episode_profile(new_name, cloned_profile)
    
    def get_episode_profile_names(self) -> List[str]:
        """Get list of all episode profile names."""
        profiles = self.load_episode_profiles()
        return list(profiles.get("profiles", {}).keys())
    
    # Import/Export Functions
    
    def export_speaker_profiles(self, profile_names: Optional[List[str]] = None) -> Dict[str, Any]:
        """Export speaker profiles to a dictionary."""
        all_profiles = self.load_speaker_profiles()
        
        if profile_names is None:
            return all_profiles
        
        # Export only specified profiles
        exported = {"profiles": {}}
        for name in profile_names:
            if name in all_profiles.get("profiles", {}):
                exported["profiles"][name] = all_profiles["profiles"][name]
        
        return exported
    
    def export_episode_profiles(self, profile_names: Optional[List[str]] = None) -> Dict[str, Any]:
        """Export episode profiles to a dictionary."""
        all_profiles = self.load_episode_profiles()
        
        if profile_names is None:
            return all_profiles
        
        # Export only specified profiles
        exported = {"profiles": {}}
        for name in profile_names:
            if name in all_profiles.get("profiles", {}):
                exported["profiles"][name] = all_profiles["profiles"][name]
        
        return exported
    
    def import_speaker_profiles(self, file_content: str) -> List[str]:
        """
        Import speaker profiles from JSON content.
        
        Args:
            file_content: JSON content as string
            
        Returns:
            List of imported profile names
        """
        try:
            import_data = json.loads(file_content)
            imported_names = []
            
            if "profiles" in import_data:
                current_profiles = self.load_speaker_profiles()
                
                for profile_name, profile_data in import_data["profiles"].items():
                    # Check if profile already exists
                    if profile_name in current_profiles.get("profiles", {}):
                        st.warning(f"Speaker profile '{profile_name}' already exists, skipping")
                        continue
                    
                    if self.create_speaker_profile(profile_name, profile_data):
                        imported_names.append(profile_name)
                
                return imported_names
            else:
                st.error("Invalid format: 'profiles' key not found")
                return []
                
        except json.JSONDecodeError as e:
            st.error(f"Invalid JSON format: {e}")
            return []
        except Exception as e:
            st.error(f"Error importing profiles: {e}")
            return []
    
    def import_episode_profiles(self, file_content: str) -> List[str]:
        """
        Import episode profiles from JSON content.
        
        Args:
            file_content: JSON content as string
            
        Returns:
            List of imported profile names
        """
        try:
            import_data = json.loads(file_content)
            imported_names = []
            
            if "profiles" in import_data:
                current_profiles = self.load_episode_profiles()
                
                for profile_name, profile_data in import_data["profiles"].items():
                    # Check if profile already exists
                    if profile_name in current_profiles.get("profiles", {}):
                        st.warning(f"Episode profile '{profile_name}' already exists, skipping")
                        continue
                    
                    if self.create_episode_profile(profile_name, profile_data):
                        imported_names.append(profile_name)
                
                return imported_names
            else:
                st.error("Invalid format: 'profiles' key not found")
                return []
                
        except json.JSONDecodeError as e:
            st.error(f"Invalid JSON format: {e}")
            return []
        except Exception as e:
            st.error(f"Error importing profiles: {e}")
            return []
    
    # Validation Functions
    
    def validate_speaker_profile(self, profile_data: Dict[str, Any]) -> List[str]:
        """
        Validate speaker profile data.
        
        Args:
            profile_data: Profile data to validate
            
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        # Check required fields
        if "tts_provider" not in profile_data:
            errors.append("TTS provider is required")
        
        if "tts_model" not in profile_data:
            errors.append("TTS model is required")
        
        if "speakers" not in profile_data:
            errors.append("Speakers list is required")
        elif not isinstance(profile_data["speakers"], list):
            errors.append("Speakers must be a list")
        elif len(profile_data["speakers"]) == 0:
            errors.append("At least one speaker is required")
        else:
            # Validate each speaker
            for i, speaker in enumerate(profile_data["speakers"]):
                if not isinstance(speaker, dict):
                    errors.append(f"Speaker {i+1} must be an object")
                    continue
                
                required_fields = ["name", "voice_id", "backstory", "personality"]
                for field in required_fields:
                    if field not in speaker:
                        errors.append(f"Speaker {i+1} missing required field: {field}")
        
        return errors
    
    def validate_episode_profile(self, profile_data: Dict[str, Any]) -> List[str]:
        """
        Validate episode profile data.
        
        Args:
            profile_data: Profile data to validate
            
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        # Check required fields
        required_fields = ["speaker_config", "outline_model", "transcript_model", "num_segments"]
        for field in required_fields:
            if field not in profile_data:
                errors.append(f"Required field missing: {field}")
        
        # Validate num_segments
        if "num_segments" in profile_data:
            try:
                num_segments = int(profile_data["num_segments"])
                if num_segments < 1 or num_segments > 10:
                    errors.append("Number of segments must be between 1 and 10")
            except (ValueError, TypeError):
                errors.append("Number of segments must be a valid integer")
        
        # Validate speaker_config exists
        if "speaker_config" in profile_data:
            speaker_names = self.get_speaker_profile_names()
            if profile_data["speaker_config"] not in speaker_names:
                errors.append(f"Speaker config '{profile_data['speaker_config']}' not found")
        
        return errors
    
    # Statistics and Info
    
    def get_profiles_stats(self) -> Dict[str, Any]:
        """Get statistics about profiles."""
        speaker_profiles = self.load_speaker_profiles()
        episode_profiles = self.load_episode_profiles()
        
        return {
            "speaker_profiles_count": len(speaker_profiles.get("profiles", {})),
            "episode_profiles_count": len(episode_profiles.get("profiles", {})),
            "total_speakers": sum(
                len(profile.get("speakers", [])) 
                for profile in speaker_profiles.get("profiles", {}).values()
            )
        }