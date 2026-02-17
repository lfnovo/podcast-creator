"""
Tests for speaker profiles functionality
"""
import json

import pytest

from podcast_creator.speakers import Speaker, SpeakerProfile, SpeakerConfig


class TestSpeakerProfile:
    """Tests for SpeakerProfile model"""

    def _make_speakers(self):
        return [
            Speaker(
                name="Alice",
                voice_id="voice_alice",
                backstory="AI researcher",
                personality="Curious and analytical",
            ),
            Speaker(
                name="Bob",
                voice_id="voice_bob",
                backstory="Software engineer",
                personality="Practical and direct",
            ),
        ]

    def test_speaker_profile_tts_config_default(self):
        """Test tts_config defaults to None"""
        profile = SpeakerProfile(
            tts_provider="openai",
            tts_model="tts-1",
            speakers=self._make_speakers(),
        )
        assert profile.tts_config is None

    def test_speaker_profile_with_tts_config(self):
        """Test speaker profile creation with tts_config"""
        profile = SpeakerProfile(
            tts_provider="elevenlabs",
            tts_model="eleven_multilingual_v2",
            speakers=self._make_speakers(),
            tts_config={
                "api_key": "sk-test",
                "base_url": "https://custom.api.com",
                "voice_settings": {"stability": 0.8},
            },
        )
        assert profile.tts_config == {
            "api_key": "sk-test",
            "base_url": "https://custom.api.com",
            "voice_settings": {"stability": 0.8},
        }

    def test_speaker_profile_from_json_with_tts_config(self, tmp_path):
        """Test loading speaker profile with tts_config from JSON"""
        config_data = {
            "profiles": {
                "custom": {
                    "tts_provider": "openai",
                    "tts_model": "tts-1",
                    "speakers": [
                        {
                            "name": "Alice",
                            "voice_id": "shimmer",
                            "backstory": "Host",
                            "personality": "Friendly",
                        }
                    ],
                    "tts_config": {"api_key": "sk-custom", "timeout": 120.0},
                }
            }
        }
        config_file = tmp_path / "speakers_config.json"
        config_file.write_text(json.dumps(config_data))

        config = SpeakerConfig.load_from_file(config_file)
        profile = config.get_profile("custom")
        assert profile.tts_config == {"api_key": "sk-custom", "timeout": 120.0}

    def test_speaker_profile_from_json_without_tts_config(self, tmp_path):
        """Test loading speaker profile without tts_config still works"""
        config_data = {
            "profiles": {
                "default": {
                    "tts_provider": "openai",
                    "tts_model": "tts-1",
                    "speakers": [
                        {
                            "name": "Alice",
                            "voice_id": "shimmer",
                            "backstory": "Host",
                            "personality": "Friendly",
                        }
                    ],
                }
            }
        }
        config_file = tmp_path / "speakers_config.json"
        config_file.write_text(json.dumps(config_data))

        config = SpeakerConfig.load_from_file(config_file)
        profile = config.get_profile("default")
        assert profile.tts_config is None


class TestSpeakerTtsOverrides:
    """Tests for per-speaker TTS override fields"""

    def test_speaker_tts_fields_default_to_none(self):
        """Test that tts_provider, tts_model, tts_config all default to None"""
        speaker = Speaker(
            name="Alice",
            voice_id="voice_alice",
            backstory="AI researcher",
            personality="Curious",
        )
        assert speaker.tts_provider is None
        assert speaker.tts_model is None
        assert speaker.tts_config is None

    def test_speaker_with_tts_overrides(self):
        """Test Speaker with all TTS override fields set"""
        speaker = Speaker(
            name="Alice",
            voice_id="voice_alice",
            backstory="AI researcher",
            personality="Curious",
            tts_provider="elevenlabs",
            tts_model="eleven_multilingual_v2",
            tts_config={"voice_settings": {"stability": 0.9}},
        )
        assert speaker.tts_provider == "elevenlabs"
        assert speaker.tts_model == "eleven_multilingual_v2"
        assert speaker.tts_config == {"voice_settings": {"stability": 0.9}}

    def test_speaker_from_json_with_tts_fields(self, tmp_path):
        """Test loading speakers with per-speaker TTS fields from JSON"""
        config_data = {
            "profiles": {
                "mixed": {
                    "tts_provider": "openai",
                    "tts_model": "tts-1",
                    "speakers": [
                        {
                            "name": "Alice",
                            "voice_id": "shimmer",
                            "backstory": "Host",
                            "personality": "Friendly",
                            "tts_provider": "elevenlabs",
                            "tts_model": "eleven_multilingual_v2",
                            "tts_config": {"api_key": "sk-eleven"},
                        },
                        {
                            "name": "Bob",
                            "voice_id": "alloy",
                            "backstory": "Guest",
                            "personality": "Analytical",
                        },
                    ],
                }
            }
        }
        config_file = tmp_path / "speakers_config.json"
        config_file.write_text(json.dumps(config_data))

        config = SpeakerConfig.load_from_file(config_file)
        profile = config.get_profile("mixed")

        alice = profile.get_speaker_by_name("Alice")
        assert alice.tts_provider == "elevenlabs"
        assert alice.tts_model == "eleven_multilingual_v2"
        assert alice.tts_config == {"api_key": "sk-eleven"}

        bob = profile.get_speaker_by_name("Bob")
        assert bob.tts_provider is None
        assert bob.tts_model is None
        assert bob.tts_config is None

    def test_speaker_from_json_without_tts_fields_backward_compat(self, tmp_path):
        """Test that existing JSON without per-speaker TTS fields still loads"""
        config_data = {
            "profiles": {
                "default": {
                    "tts_provider": "openai",
                    "tts_model": "tts-1",
                    "speakers": [
                        {
                            "name": "Alice",
                            "voice_id": "shimmer",
                            "backstory": "Host",
                            "personality": "Friendly",
                        }
                    ],
                }
            }
        }
        config_file = tmp_path / "speakers_config.json"
        config_file.write_text(json.dumps(config_data))

        config = SpeakerConfig.load_from_file(config_file)
        profile = config.get_profile("default")
        alice = profile.get_speaker_by_name("Alice")
        assert alice.tts_provider is None
        assert alice.tts_model is None
        assert alice.tts_config is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
