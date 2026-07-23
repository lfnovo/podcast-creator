"""Regression tests for durable podcast generation progress callbacks."""

import asyncio
from unittest.mock import MagicMock, patch

from podcast_creator.core import Dialogue, Outline, Segment
from podcast_creator.graph import create_podcast


class FakeGraph:
    """Minimal async graph stream that repeats each completed state."""

    def __init__(self, states):
        self.states = states
        self.calls = []

    async def astream(self, initial_state, *, config, stream_mode):
        self.calls.append((initial_state, config, stream_mode))
        for state in self.states:
            yield state


def test_create_podcast_emits_outline_and_transcript_before_audio(tmp_path):
    outline = Outline(
        segments=[Segment(name="Intro", description="An introduction")]
    )
    transcript = [Dialogue(speaker="Host", dialogue="Welcome")]
    final_path = tmp_path / "episode.mp3"
    states = [
        {
            "outline": None,
            "transcript": [],
            "audio_clips": [],
            "final_output_file_path": None,
        },
        {
            "outline": outline,
            "transcript": [],
            "audio_clips": [],
            "final_output_file_path": None,
        },
        {
            "outline": outline,
            "transcript": transcript,
            "audio_clips": [],
            "final_output_file_path": None,
        },
        {
            "outline": outline,
            "transcript": transcript,
            "audio_clips": [tmp_path / "clip.mp3"],
            "final_output_file_path": final_path,
        },
    ]
    fake_graph = FakeGraph(states)
    progress = []

    async def record_progress(stage, value):
        progress.append((stage, value))

    with (
        patch("podcast_creator.graph.graph", fake_graph),
        patch("podcast_creator.graph.load_speaker_config", return_value=MagicMock()),
    ):
        result = asyncio.run(
            create_podcast(
                content="source",
                briefing="brief",
                episode_name="episode",
                output_dir=str(tmp_path),
                speaker_config="speakers",
                progress_callback=record_progress,
            )
        )

    assert fake_graph.calls[0][2] == "values"
    assert [stage for stage, _ in progress] == ["outline", "transcript"]
    assert progress[0][1] is outline
    assert progress[1][1] is transcript
    assert result["outline"] is outline
    assert result["transcript"] is transcript
    assert result["final_output_file_path"] == final_path
    assert (tmp_path / "outline.json").exists()
    assert (tmp_path / "transcript.json").exists()
