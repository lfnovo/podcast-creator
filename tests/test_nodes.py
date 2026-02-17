"""
Tests for node config merging logic
"""
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from pathlib import Path

from podcast_creator.nodes import (
    generate_outline_node,
    generate_transcript_node,
    generate_single_audio_clip,
)


def _setup_language_mocks(mock_factory, mock_prompter, mock_parser):
    """Helper to wire up common mocks for LLM node tests."""
    mock_lc = MagicMock()
    mock_lc.ainvoke = AsyncMock(return_value=MagicMock(content='{"segments": []}'))
    mock_model = MagicMock()
    mock_model.to_langchain.return_value = mock_lc
    mock_factory.create_language.return_value = mock_model
    mock_prompter.return_value.render.return_value = "prompt"
    mock_parser.invoke.return_value = MagicMock(segments=[])


class TestOutlineConfigMerging:
    """Tests for outline config merging in generate_outline_node"""

    @patch("podcast_creator.nodes.AIFactory")
    @patch("podcast_creator.nodes.get_outline_prompter")
    @patch("podcast_creator.nodes.outline_parser")
    def test_empty_config_preserves_defaults(
        self, mock_parser, mock_prompter, mock_factory
    ):
        """Test that empty outline_config preserves default max_tokens and structured"""
        _setup_language_mocks(mock_factory, mock_prompter, mock_parser)

        state = {
            "briefing": "test",
            "num_segments": 3,
            "content": "content",
            "speaker_profile": MagicMock(speakers=[]),
        }
        config = {"configurable": {"outline_config": {}}}

        asyncio.run(generate_outline_node(state, config))

        mock_factory.create_language.assert_called_once_with(
            "openai",
            "gpt-4o-mini",
            config={"max_tokens": 3000, "structured": {"type": "json"}},
        )

    @patch("podcast_creator.nodes.AIFactory")
    @patch("podcast_creator.nodes.get_outline_prompter")
    @patch("podcast_creator.nodes.outline_parser")
    def test_user_config_overrides_defaults(
        self, mock_parser, mock_prompter, mock_factory
    ):
        """Test that user config overrides default max_tokens"""
        _setup_language_mocks(mock_factory, mock_prompter, mock_parser)

        state = {
            "briefing": "test",
            "num_segments": 3,
            "content": "content",
            "speaker_profile": MagicMock(speakers=[]),
        }
        config = {"configurable": {"outline_config": {"max_tokens": 6000}}}

        asyncio.run(generate_outline_node(state, config))

        mock_factory.create_language.assert_called_once_with(
            "openai",
            "gpt-4o-mini",
            config={"max_tokens": 6000, "structured": {"type": "json"}},
        )

    @patch("podcast_creator.nodes.AIFactory")
    @patch("podcast_creator.nodes.get_outline_prompter")
    @patch("podcast_creator.nodes.outline_parser")
    def test_user_config_adds_new_keys(
        self, mock_parser, mock_prompter, mock_factory
    ):
        """Test that user config can add new keys like temperature"""
        _setup_language_mocks(mock_factory, mock_prompter, mock_parser)

        state = {
            "briefing": "test",
            "num_segments": 3,
            "content": "content",
            "speaker_profile": MagicMock(speakers=[]),
        }
        config = {"configurable": {"outline_config": {"temperature": 0.7}}}

        asyncio.run(generate_outline_node(state, config))

        mock_factory.create_language.assert_called_once_with(
            "openai",
            "gpt-4o-mini",
            config={
                "max_tokens": 3000,
                "structured": {"type": "json"},
                "temperature": 0.7,
            },
        )

    @patch("podcast_creator.nodes.AIFactory")
    @patch("podcast_creator.nodes.get_outline_prompter")
    @patch("podcast_creator.nodes.outline_parser")
    def test_none_config_preserves_defaults(
        self, mock_parser, mock_prompter, mock_factory
    ):
        """Test that None outline_config preserves defaults"""
        _setup_language_mocks(mock_factory, mock_prompter, mock_parser)

        state = {
            "briefing": "test",
            "num_segments": 3,
            "content": "content",
            "speaker_profile": MagicMock(speakers=[]),
        }
        config = {"configurable": {}}

        asyncio.run(generate_outline_node(state, config))

        mock_factory.create_language.assert_called_once_with(
            "openai",
            "gpt-4o-mini",
            config={"max_tokens": 3000, "structured": {"type": "json"}},
        )


class TestTranscriptConfigMerging:
    """Tests for transcript config merging in generate_transcript_node"""

    @patch("podcast_creator.nodes.AIFactory")
    @patch("podcast_creator.nodes.get_transcript_prompter")
    @patch("podcast_creator.nodes.create_validated_transcript_parser")
    def test_user_config_overrides_transcript_defaults(
        self, mock_parser_factory, mock_prompter, mock_factory
    ):
        """Test that user config overrides default transcript max_tokens"""
        mock_lc = MagicMock()
        mock_lc.ainvoke = AsyncMock(
            return_value=MagicMock(content='{"transcript": []}')
        )
        mock_model = MagicMock()
        mock_model.to_langchain.return_value = mock_lc
        mock_factory.create_language.return_value = mock_model

        mock_prompter.return_value.render.return_value = "prompt"
        mock_parser = MagicMock()
        mock_parser.invoke.return_value = MagicMock(transcript=[])
        mock_parser_factory.return_value = mock_parser

        outline = MagicMock()
        outline.segments = []
        speaker_profile = MagicMock()
        speaker_profile.get_speaker_names.return_value = ["Alice", "Bob"]

        state = {
            "briefing": "test",
            "content": "content",
            "outline": outline,
            "speaker_profile": speaker_profile,
        }
        config = {
            "configurable": {
                "transcript_config": {"max_tokens": 10000, "temperature": 0.8}
            }
        }

        asyncio.run(generate_transcript_node(state, config))

        mock_factory.create_language.assert_called_once_with(
            "openai",
            "gpt-4o-mini",
            config={
                "max_tokens": 10000,
                "structured": {"type": "json"},
                "temperature": 0.8,
            },
        )


class TestTtsConfigPassthrough:
    """Tests for TTS config passthrough in generate_single_audio_clip"""

    @patch("podcast_creator.nodes.AIFactory")
    def test_tts_config_extracts_api_key_and_base_url(self, mock_factory):
        """Test that api_key and base_url are extracted from tts_config"""
        mock_tts = MagicMock()
        mock_tts.agenerate_speech = AsyncMock()
        mock_factory.create_text_to_speech.return_value = mock_tts

        dialogue = MagicMock()
        dialogue.speaker = "Alice"
        dialogue.dialogue = "Hello world"

        dialogue_info = {
            "dialogue": dialogue,
            "index": 0,
            "output_dir": Path("/tmp/test_output"),
            "tts_provider": "elevenlabs",
            "tts_model": "eleven_multilingual_v2",
            "voices": {"Alice": "voice_alice"},
            "tts_config": {
                "api_key": "sk-custom",
                "base_url": "https://custom.api.com",
                "voice_settings": {"stability": 0.8},
            },
        }

        with patch("pathlib.Path.mkdir"):
            asyncio.run(generate_single_audio_clip(dialogue_info))

        mock_factory.create_text_to_speech.assert_called_once_with(
            "elevenlabs",
            "eleven_multilingual_v2",
            api_key="sk-custom",
            base_url="https://custom.api.com",
            voice_settings={"stability": 0.8},
        )

    @patch("podcast_creator.nodes.AIFactory")
    def test_tts_config_empty_passes_none_for_named_params(self, mock_factory):
        """Test that empty tts_config passes None for api_key and base_url"""
        mock_tts = MagicMock()
        mock_tts.agenerate_speech = AsyncMock()
        mock_factory.create_text_to_speech.return_value = mock_tts

        dialogue = MagicMock()
        dialogue.speaker = "Alice"
        dialogue.dialogue = "Hello"

        dialogue_info = {
            "dialogue": dialogue,
            "index": 0,
            "output_dir": Path("/tmp/test_output"),
            "tts_provider": "openai",
            "tts_model": "tts-1",
            "voices": {"Alice": "shimmer"},
            "tts_config": {},
        }

        with patch("pathlib.Path.mkdir"):
            asyncio.run(generate_single_audio_clip(dialogue_info))

        mock_factory.create_text_to_speech.assert_called_once_with(
            "openai", "tts-1", api_key=None, base_url=None
        )

    @patch("podcast_creator.nodes.AIFactory")
    def test_tts_config_missing_defaults_to_empty(self, mock_factory):
        """Test that missing tts_config key defaults to empty dict behavior"""
        mock_tts = MagicMock()
        mock_tts.agenerate_speech = AsyncMock()
        mock_factory.create_text_to_speech.return_value = mock_tts

        dialogue = MagicMock()
        dialogue.speaker = "Alice"
        dialogue.dialogue = "Hello"

        dialogue_info = {
            "dialogue": dialogue,
            "index": 0,
            "output_dir": Path("/tmp/test_output"),
            "tts_provider": "openai",
            "tts_model": "tts-1",
            "voices": {"Alice": "shimmer"},
        }

        with patch("pathlib.Path.mkdir"):
            asyncio.run(generate_single_audio_clip(dialogue_info))

        mock_factory.create_text_to_speech.assert_called_once_with(
            "openai", "tts-1", api_key=None, base_url=None
        )

    @patch("podcast_creator.nodes.AIFactory")
    def test_tts_config_does_not_mutate_original(self, mock_factory):
        """Test that extracting api_key/base_url doesn't mutate the original dict"""
        mock_tts = MagicMock()
        mock_tts.agenerate_speech = AsyncMock()
        mock_factory.create_text_to_speech.return_value = mock_tts

        dialogue = MagicMock()
        dialogue.speaker = "Alice"
        dialogue.dialogue = "Hello"

        original_config = {"api_key": "sk-test", "timeout": 120.0}
        dialogue_info = {
            "dialogue": dialogue,
            "index": 0,
            "output_dir": Path("/tmp/test_output"),
            "tts_provider": "openai",
            "tts_model": "tts-1",
            "voices": {"Alice": "shimmer"},
            "tts_config": original_config,
        }

        with patch("pathlib.Path.mkdir"):
            asyncio.run(generate_single_audio_clip(dialogue_info))

        # Original dict should not be mutated
        assert "api_key" in original_config


class TestPerSpeakerTtsOverride:
    """Tests for per-speaker TTS override resolution in generate_all_audio_node"""

    def _make_state(self, speakers, transcript_speakers):
        """Helper to build a minimal state for generate_all_audio_node."""
        from podcast_creator.speakers import Speaker, SpeakerProfile

        speaker_objs = []
        for s in speakers:
            speaker_objs.append(Speaker(**s))

        profile = SpeakerProfile(
            tts_provider="openai",
            tts_model="tts-1",
            speakers=speaker_objs,
            tts_config={"api_key": "sk-profile", "stability": 0.5},
        )

        transcript = []
        for name in transcript_speakers:
            d = MagicMock()
            d.speaker = name
            d.dialogue = f"Hello from {name}"
            transcript.append(d)

        return {
            "transcript": transcript,
            "output_dir": Path("/tmp/test_output"),
            "speaker_profile": profile,
        }

    @patch("podcast_creator.nodes.generate_single_audio_clip", new_callable=AsyncMock)
    @patch("podcast_creator.nodes.asyncio.sleep", new_callable=AsyncMock)
    def test_speaker_tts_provider_override(self, mock_sleep, mock_gen_clip):
        """Speaker with tts_provider override uses speaker's provider"""
        mock_gen_clip.return_value = Path("/tmp/clip.mp3")

        state = self._make_state(
            speakers=[
                {
                    "name": "Alice",
                    "voice_id": "v1",
                    "backstory": "b",
                    "personality": "p",
                    "tts_provider": "elevenlabs",
                },
                {
                    "name": "Bob",
                    "voice_id": "v2",
                    "backstory": "b",
                    "personality": "p",
                },
            ],
            transcript_speakers=["Alice", "Bob"],
        )

        from podcast_creator.nodes import generate_all_audio_node

        asyncio.run(generate_all_audio_node(state, {"configurable": {}}))

        calls = mock_gen_clip.call_args_list
        alice_info = calls[0][0][0]
        bob_info = calls[1][0][0]

        assert alice_info["tts_provider"] == "elevenlabs"
        assert bob_info["tts_provider"] == "openai"

    @patch("podcast_creator.nodes.generate_single_audio_clip", new_callable=AsyncMock)
    @patch("podcast_creator.nodes.asyncio.sleep", new_callable=AsyncMock)
    def test_speaker_tts_model_override(self, mock_sleep, mock_gen_clip):
        """Speaker with tts_model override uses speaker's model"""
        mock_gen_clip.return_value = Path("/tmp/clip.mp3")

        state = self._make_state(
            speakers=[
                {
                    "name": "Alice",
                    "voice_id": "v1",
                    "backstory": "b",
                    "personality": "p",
                    "tts_model": "eleven_multilingual_v2",
                },
                {
                    "name": "Bob",
                    "voice_id": "v2",
                    "backstory": "b",
                    "personality": "p",
                },
            ],
            transcript_speakers=["Alice", "Bob"],
        )

        from podcast_creator.nodes import generate_all_audio_node

        asyncio.run(generate_all_audio_node(state, {"configurable": {}}))

        calls = mock_gen_clip.call_args_list
        alice_info = calls[0][0][0]
        bob_info = calls[1][0][0]

        assert alice_info["tts_model"] == "eleven_multilingual_v2"
        assert bob_info["tts_model"] == "tts-1"

    @patch("podcast_creator.nodes.generate_single_audio_clip", new_callable=AsyncMock)
    @patch("podcast_creator.nodes.asyncio.sleep", new_callable=AsyncMock)
    def test_speaker_tts_config_override_replaces_profile(self, mock_sleep, mock_gen_clip):
        """Speaker with tts_config replaces profile config entirely (no merge)"""
        mock_gen_clip.return_value = Path("/tmp/clip.mp3")

        state = self._make_state(
            speakers=[
                {
                    "name": "Alice",
                    "voice_id": "v1",
                    "backstory": "b",
                    "personality": "p",
                    "tts_config": {"api_key": "sk-alice", "speed": 1.2},
                },
                {
                    "name": "Bob",
                    "voice_id": "v2",
                    "backstory": "b",
                    "personality": "p",
                },
            ],
            transcript_speakers=["Alice", "Bob"],
        )

        from podcast_creator.nodes import generate_all_audio_node

        asyncio.run(generate_all_audio_node(state, {"configurable": {}}))

        calls = mock_gen_clip.call_args_list
        alice_info = calls[0][0][0]
        bob_info = calls[1][0][0]

        # Alice gets her own config (no profile keys merged in)
        assert alice_info["tts_config"] == {"api_key": "sk-alice", "speed": 1.2}
        # Bob falls back to profile config
        assert bob_info["tts_config"] == {"api_key": "sk-profile", "stability": 0.5}

    @patch("podcast_creator.nodes.generate_single_audio_clip", new_callable=AsyncMock)
    @patch("podcast_creator.nodes.asyncio.sleep", new_callable=AsyncMock)
    def test_speaker_empty_tts_config_does_not_fallthrough(self, mock_sleep, mock_gen_clip):
        """Speaker with tts_config={} does NOT fall through to profile config"""
        mock_gen_clip.return_value = Path("/tmp/clip.mp3")

        state = self._make_state(
            speakers=[
                {
                    "name": "Alice",
                    "voice_id": "v1",
                    "backstory": "b",
                    "personality": "p",
                    "tts_config": {},
                },
                {
                    "name": "Bob",
                    "voice_id": "v2",
                    "backstory": "b",
                    "personality": "p",
                },
            ],
            transcript_speakers=["Alice"],
        )

        from podcast_creator.nodes import generate_all_audio_node

        asyncio.run(generate_all_audio_node(state, {"configurable": {}}))

        calls = mock_gen_clip.call_args_list
        alice_info = calls[0][0][0]

        # Empty dict is respected, not replaced by profile config
        assert alice_info["tts_config"] == {}

    @patch("podcast_creator.nodes.generate_single_audio_clip", new_callable=AsyncMock)
    @patch("podcast_creator.nodes.asyncio.sleep", new_callable=AsyncMock)
    def test_speaker_without_overrides_uses_profile(self, mock_sleep, mock_gen_clip):
        """Speaker without any TTS overrides falls back to profile-level values"""
        mock_gen_clip.return_value = Path("/tmp/clip.mp3")

        state = self._make_state(
            speakers=[
                {
                    "name": "Alice",
                    "voice_id": "v1",
                    "backstory": "b",
                    "personality": "p",
                },
            ],
            transcript_speakers=["Alice"],
        )

        from podcast_creator.nodes import generate_all_audio_node

        asyncio.run(generate_all_audio_node(state, {"configurable": {}}))

        calls = mock_gen_clip.call_args_list
        alice_info = calls[0][0][0]

        assert alice_info["tts_provider"] == "openai"
        assert alice_info["tts_model"] == "tts-1"
        assert alice_info["tts_config"] == {"api_key": "sk-profile", "stability": 0.5}


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
