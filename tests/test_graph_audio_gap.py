"""
Tests for audio_gap_ms resolution in create_podcast
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from podcast_creator.episodes import EpisodeProfile
from podcast_creator.graph import create_podcast


def _run(tmp_path, profile=None, **kwargs):
    """Run create_podcast with the graph mocked; return the configurable it received."""
    fake_graph = MagicMock()
    fake_graph.ainvoke = AsyncMock(
        return_value={
            "outline": None,
            "transcript": [],
            "final_output_file_path": None,
            "audio_clips": [],
        }
    )
    with patch("podcast_creator.graph.graph", fake_graph), patch(
        "podcast_creator.graph.load_speaker_config", return_value=MagicMock()
    ), patch("podcast_creator.graph.load_episode_config", return_value=profile):
        asyncio.run(
            create_podcast(
                content="content",
                episode_name="episode",
                output_dir=str(tmp_path),
                episode_profile="profile" if profile else None,
                speaker_config=None if profile else "speakers",
                briefing=None if profile else "briefing",
                **kwargs,
            )
        )
    return fake_graph.ainvoke.call_args.kwargs["config"]["configurable"]


def _profile(**kwargs):
    return EpisodeProfile(speaker_config="speakers", default_briefing="briefing", **kwargs)


class TestAudioGapResolution:
    def test_argument_overrides_profile(self, tmp_path):
        configurable = _run(tmp_path, _profile(audio_gap_ms=800), audio_gap_ms=200)
        assert configurable["audio_gap_ms"] == 200

    def test_zero_argument_overrides_profile(self, tmp_path):
        configurable = _run(tmp_path, _profile(audio_gap_ms=800), audio_gap_ms=0)
        assert configurable["audio_gap_ms"] == 0

    def test_profile_value_used_without_argument(self, tmp_path):
        configurable = _run(tmp_path, _profile(audio_gap_ms=800))
        assert configurable["audio_gap_ms"] == 800

    def test_profile_default_is_400(self, tmp_path):
        configurable = _run(tmp_path, _profile())
        assert configurable["audio_gap_ms"] == 400

    def test_without_profile_node_default_applies(self, tmp_path):
        configurable = _run(tmp_path)
        assert "audio_gap_ms" not in configurable

    @pytest.mark.parametrize("value", [-1, 1.5, True])
    def test_invalid_argument_rejected_before_generation(self, tmp_path, value):
        with pytest.raises(ValueError, match="audio_gap_ms"):
            _run(tmp_path, audio_gap_ms=value)

    def test_negative_profile_value_rejected(self):
        with pytest.raises(ValidationError):
            _profile(audio_gap_ms=-1)
