"""
Tests for episode profiles functionality
"""
import pytest
import json
from pydantic import ValidationError

from podcast_creator.episodes import EpisodeProfile, EpisodeConfig, load_episode_config
from podcast_creator.config import configure, ConfigurationManager


class TestEpisodeProfile:
    """Tests for EpisodeProfile model"""

    def test_episode_profile_creation(self):
        """Test basic episode profile creation and validation"""
        profile = EpisodeProfile(
            speaker_config="ai_researchers",
            outline_provider="openai",
            outline_model="gpt-4o-mini",
            transcript_provider="anthropic",
            transcript_model="claude-3-5-sonnet-latest",
            default_briefing="Test briefing",
            num_segments=3
        )
        
        assert profile.speaker_config == "ai_researchers"
        assert profile.outline_provider == "openai"
        assert profile.outline_model == "gpt-4o-mini"
        assert profile.transcript_provider == "anthropic"
        assert profile.transcript_model == "claude-3-5-sonnet-latest"
        assert profile.default_briefing == "Test briefing"
        assert profile.num_segments == 3

    def test_episode_profile_defaults(self):
        """Test episode profile with default values"""
        profile = EpisodeProfile(speaker_config="ai_researchers")
        
        assert profile.speaker_config == "ai_researchers"
        assert profile.outline_provider == "openai"
        assert profile.outline_model == "gpt-4o-mini"
        assert profile.transcript_provider == "anthropic"
        assert profile.transcript_model == "claude-3-5-sonnet-latest"
        assert profile.default_briefing == ""
        assert profile.num_segments == 3

    def test_episode_profile_validation_speaker_config(self):
        """Test speaker config validation"""
        with pytest.raises(ValueError, match="Speaker config cannot be empty"):
            EpisodeProfile(speaker_config="")
        
        with pytest.raises(ValueError, match="Speaker config cannot be empty"):
            EpisodeProfile(speaker_config="   ")

    def test_episode_profile_validation_num_segments(self):
        """Test num_segments validation"""
        with pytest.raises(ValueError, match="between 1 and 10"):
            EpisodeProfile(speaker_config="ai_researchers", num_segments=0)
        
        with pytest.raises(ValueError, match="between 1 and 10"):
            EpisodeProfile(speaker_config="ai_researchers", num_segments=15)

    def test_episode_profile_validation_providers(self):
        """Test provider validation"""
        with pytest.raises(ValueError, match="Provider cannot be empty"):
            EpisodeProfile(speaker_config="ai_researchers", outline_provider="")
        
        with pytest.raises(ValueError, match="Provider cannot be empty"):
            EpisodeProfile(speaker_config="ai_researchers", transcript_provider="")

    def test_episode_profile_validation_models(self):
        """Test model validation"""
        with pytest.raises(ValueError, match="Model cannot be empty"):
            EpisodeProfile(speaker_config="ai_researchers", outline_model="")
        
        with pytest.raises(ValueError, match="Model cannot be empty"):
            EpisodeProfile(speaker_config="ai_researchers", transcript_model="")


class TestEpisodeConfig:
    """Tests for EpisodeConfig model"""

    def test_episode_config_creation(self):
        """Test episode config with multiple profiles"""
        config = EpisodeConfig(
            profiles={
                "test_profile": EpisodeProfile(
                    speaker_config="ai_researchers",
                    default_briefing="Test briefing"
                ),
                "another_profile": EpisodeProfile(
                    speaker_config="solo_expert",
                    default_briefing="Another briefing"
                )
            }
        )
        
        assert len(config.profiles) == 2
        assert "test_profile" in config.profiles
        assert "another_profile" in config.profiles

    def test_episode_config_get_profile(self):
        """Test getting profile by name"""
        config = EpisodeConfig(
            profiles={
                "test_profile": EpisodeProfile(
                    speaker_config="ai_researchers",
                    default_briefing="Test briefing"
                )
            }
        )
        
        profile = config.get_profile("test_profile")
        assert profile.speaker_config == "ai_researchers"
        assert profile.default_briefing == "Test briefing"

    def test_episode_config_get_profile_not_found(self):
        """Test getting non-existent profile"""
        config = EpisodeConfig(
            profiles={
                "test_profile": EpisodeProfile(speaker_config="ai_researchers")
            }
        )
        
        with pytest.raises(ValueError, match="Episode profile 'nonexistent' not found"):
            config.get_profile("nonexistent")

    def test_episode_config_list_profiles(self):
        """Test listing profile names"""
        config = EpisodeConfig(
            profiles={
                "profile1": EpisodeProfile(speaker_config="ai_researchers"),
                "profile2": EpisodeProfile(speaker_config="solo_expert")
            }
        )
        
        profiles = config.list_profiles()
        assert set(profiles) == {"profile1", "profile2"}

    def test_episode_config_validation_empty_profiles(self):
        """Test validation with empty profiles"""
        with pytest.raises(ValueError, match="At least one episode profile must be defined"):
            EpisodeConfig(profiles={})

    def test_episode_config_load_from_file(self, tmp_path):
        """Test loading episode config from file"""
        config_data = {
            "profiles": {
                "test_profile": {
                    "speaker_config": "ai_researchers",
                    "default_briefing": "Test briefing"
                }
            }
        }
        
        config_file = tmp_path / "episodes_config.json"
        config_file.write_text(json.dumps(config_data))
        
        config = EpisodeConfig.load_from_file(config_file)
        assert len(config.profiles) == 1
        assert "test_profile" in config.profiles
        assert config.profiles["test_profile"].speaker_config == "ai_researchers"

    def test_episode_config_load_from_file_not_found(self, tmp_path):
        """Test loading from non-existent file"""
        nonexistent_file = tmp_path / "nonexistent.json"
        
        with pytest.raises(FileNotFoundError, match="Episode config file not found"):
            EpisodeConfig.load_from_file(nonexistent_file)

    def test_episode_config_load_from_file_invalid_json(self, tmp_path):
        """Test loading from file with invalid JSON"""
        config_file = tmp_path / "invalid.json"
        config_file.write_text("{invalid json")
        
        with pytest.raises(ValueError, match="Invalid JSON in episode config file"):
            EpisodeConfig.load_from_file(config_file)


class TestLoadEpisodeConfig:
    """Tests for load_episode_config function"""

    def test_load_episode_config_bundled_defaults(self):
        """Test loading episode config from bundled defaults"""
        profile = load_episode_config("tech_discussion")
        
        assert profile.speaker_config == "ai_researchers"
        assert profile.outline_provider == "openai"
        assert profile.outline_model == "gpt-4o-mini"
        assert profile.transcript_provider == "anthropic"
        assert profile.transcript_model == "claude-3-5-sonnet-latest"
        assert profile.num_segments == 4
        assert "engaging and informative discussion" in profile.default_briefing.lower()

    def test_load_episode_config_bundled_solo_expert(self):
        """Test loading solo expert profile"""
        profile = load_episode_config("solo_expert")
        
        assert profile.speaker_config == "solo_expert"
        assert profile.num_segments == 3
        assert "educational and approachable" in profile.default_briefing.lower()

    def test_load_episode_config_not_found(self):
        """Test loading non-existent episode config"""
        with pytest.raises(ValueError, match="Episode profile 'nonexistent' not found"):
            load_episode_config("nonexistent")

    def test_load_episode_config_inline_configuration(self):
        """Test loading from inline configuration"""
        # Configure inline episode config
        configure("episode_config", {
            "profiles": {
                "test_inline": {
                    "speaker_config": "ai_researchers",
                    "outline_provider": "openai",
                    "outline_model": "gpt-4o-mini",
                    "transcript_provider": "anthropic",
                    "transcript_model": "claude-3-5-sonnet-latest",
                    "default_briefing": "Inline test briefing",
                    "num_segments": 5
                }
            }
        })
        
        profile = load_episode_config("test_inline")
        
        assert profile.speaker_config == "ai_researchers"
        assert profile.default_briefing == "Inline test briefing"
        assert profile.num_segments == 5

    def test_load_episode_config_working_directory(self, tmp_path, monkeypatch):
        """Test loading from working directory"""
        # Change to temp directory
        monkeypatch.chdir(tmp_path)
        
        # Create episode config file
        config_data = {
            "profiles": {
                "local_profile": {
                    "speaker_config": "ai_researchers",
                    "default_briefing": "Local test briefing"
                }
            }
        }
        
        config_file = tmp_path / "episodes_config.json"
        config_file.write_text(json.dumps(config_data))
        
        profile = load_episode_config("local_profile")
        
        assert profile.speaker_config == "ai_researchers"
        assert profile.default_briefing == "Local test briefing"


class TestConfigurationIntegration:
    """Tests for episode configuration integration"""

    def test_configure_episode_config_dict(self):
        """Test configuring episode config with dictionary"""
        config_manager = ConfigurationManager()
        
        config_manager.configure("episode_config", {
            "profiles": {
                "test_profile": {
                    "speaker_config": "ai_researchers",
                    "default_briefing": "Test briefing"
                }
            }
        })
        
        profile = config_manager.get_episode_profile("test_profile")
        assert profile is not None
        assert profile.speaker_config == "ai_researchers"
        assert profile.default_briefing == "Test briefing"

    def test_configure_episode_config_file_path(self, tmp_path):
        """Test configuring episode config with file path"""
        config_manager = ConfigurationManager()
        
        # Create config file
        config_data = {
            "profiles": {
                "file_profile": {
                    "speaker_config": "ai_researchers",
                    "default_briefing": "File test briefing"
                }
            }
        }
        
        config_file = tmp_path / "episodes_config.json"
        config_file.write_text(json.dumps(config_data))
        
        config_manager.configure("episode_config", str(config_file))
        
        # This tests the validation, not the loading (which happens in load_episode_config)
        config = config_manager.get_config("episode_config")
        assert config == str(config_file)

    def test_get_episode_profile_not_found(self):
        """Test getting non-existent episode profile"""
        config_manager = ConfigurationManager()
        
        profile = config_manager.get_episode_profile("nonexistent")
        assert profile is None

    def test_configure_invalid_episode_config(self):
        """Test configuring invalid episode config"""
        config_manager = ConfigurationManager()
        
        with pytest.raises(ValidationError):
            config_manager.configure("episode_config", {
                "profiles": {
                    "invalid_profile": {
                        # Missing required speaker_config
                    }
                }
            })

    def test_configure_episode_config_invalid_file(self, tmp_path):
        """Test configuring episode config with invalid file"""
        config_manager = ConfigurationManager()
        
        # Test non-existent file
        with pytest.raises(ValueError, match="Episode config file not found"):
            config_manager.configure("episode_config", str(tmp_path / "nonexistent.json"))
        
        # Test non-JSON file
        txt_file = tmp_path / "config.txt"
        txt_file.write_text("not json")
        
        with pytest.raises(ValueError, match="Episode config must be a JSON file"):
            config_manager.configure("episode_config", str(txt_file))


if __name__ == "__main__":
    pytest.main([__file__, "-v"])