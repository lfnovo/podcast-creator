"""Multi-speaker grouping, request wiring and regeneration regression tests."""

import asyncio
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from podcast_creator.audio_groups import format_dialogue, group_dialogue
from podcast_creator.core import Dialogue
from podcast_creator.nodes import generate_all_audio_node, regenerate_audio_group
from podcast_creator.speakers import SpeakerConfig, SpeakerProfile, load_speaker_config


def profile_data(**kwargs):
    return dict(
        tts_provider="elevenlabs",
        tts_model="eleven_v3",
        multi_speaker=True,
        speakers=[
            dict(name=name, voice_id=f"voice-{name}", backstory="b", personality="p")
            for name in ("A", "B")
        ],
        **kwargs,
    )


def turns(names, size=10):
    return [Dialogue(speaker=name, dialogue="x" * size) for name in names]


@pytest.fixture
def tts():
    async def write_audio(**kwargs):
        kwargs["output_file"].write_bytes(b"new audio")

    model = SimpleNamespace(
        agenerate_multi_speaker_speech=AsyncMock(side_effect=write_audio)
    )
    with patch(
        "podcast_creator.speakers.AIFactory.create_text_to_speech", return_value=model
    ):
        yield model


def test_default_does_not_construct_model():
    data = profile_data()
    del data["multi_speaker"]
    with patch("podcast_creator.speakers.AIFactory.create_text_to_speech") as factory:
        assert not SpeakerProfile(**data).multi_speaker
        factory.assert_not_called()


def test_unsupported_provider_at_file_load(tmp_path):
    data = profile_data()
    data["tts_provider"] = "openai"
    path = tmp_path / "speakers_config.json"
    path.write_text(json.dumps({"profiles": {"test": data}}))
    with patch(
        "podcast_creator.speakers.AIFactory.create_text_to_speech",
        return_value=object(),
    ):
        with pytest.raises(ValueError, match="openai.*does not support multi-speaker"):
            SpeakerConfig.load_from_file(path)


@pytest.mark.parametrize("name", ["A:B", "A\nB", "A\rB"])
def test_reject_parser_unsafe_names(name):
    data = profile_data()
    data["speakers"][0]["name"] = name
    with pytest.raises(ValueError, match="colons or line breaks"):
        SpeakerProfile(**data)


def test_reject_per_speaker_overrides():
    data = profile_data()
    data["speakers"][0]["tts_config"] = {}
    with pytest.raises(ValueError, match="shared TTS configuration"):
        SpeakerProfile(**data)


def test_configured_file_failure_does_not_fall_back(tmp_path):
    path = tmp_path / "profiles.json"
    path.write_text(json.dumps({"profiles": {"test": profile_data()}}))
    with (
        patch("podcast_creator.config.ConfigurationManager") as manager,
        patch(
            "podcast_creator.speakers.AIFactory.create_text_to_speech",
            return_value=object(),
        ),
    ):
        manager.return_value.get_speaker_profile.return_value = None
        manager.return_value.get_config.return_value = str(path)
        with pytest.raises(ValueError, match="does not support multi-speaker"):
            load_speaker_config("test", tmp_path)


def test_inline_failure_does_not_fall_back():
    from podcast_creator.config import ConfigurationManager

    with (
        patch.object(
            ConfigurationManager,
            "get_config",
            return_value={"profiles": {"test": profile_data()}},
        ),
        patch(
            "podcast_creator.speakers.AIFactory.create_text_to_speech",
            return_value=object(),
        ),
    ):
        with pytest.raises(ValueError, match="does not support multi-speaker"):
            load_speaker_config("test")


def test_format_normalizes_embedded_newlines():
    assert format_dialogue(
        [Dialogue(speaker="A", dialogue="Hi\nB: still A\r\nYes")]
    ) == ("A: Hi B: still A Yes")


def test_section_boundary_wins_over_fuller_speaker_change():
    transcript = turns("ABABA")  # Each formatted turn is 13 chars.
    groups = group_dialogue(transcript, 41, section_starts=[2])
    assert list(map(len, groups)) == [2, 3]
    assert [turn for group in groups for turn in group] == transcript


def test_speaker_change_wins_over_packing():
    assert list(map(len, group_dialogue(turns("ABBB"), 41))) == [1, 3]


def test_whole_turn_fallback_and_exact_limit():
    transcript = turns("AAAA")
    assert list(map(len, group_dialogue(transcript, 27))) == [2, 2]
    assert list(map(len, group_dialogue(transcript, 55))) == [4]
    assert group_dialogue([], 2000) == []
    with pytest.raises(ValueError, match="Turn 0.*shorten"):
        group_dialogue(transcript, 12)
    with pytest.raises(ValueError, match="zero-based"):
        group_dialogue(transcript, 41, [-1])


def test_grouped_requests_batching_seed_and_stale_clips(tts, tmp_path, monkeypatch):
    monkeypatch.setenv("TTS_BATCH_SIZE", "2")
    profile = SpeakerProfile(
        **profile_data(tts_config={"seed": 0, "settings": {"stability": 0.5}})
    )
    transcript = turns("ABABABA", 900)
    clips = tmp_path / "clips"
    clips.mkdir()
    (clips / "0006.mp3").write_bytes(b"stale")
    state = {
        "transcript": transcript,
        "output_dir": tmp_path,
        "speaker_profile": profile,
    }
    with patch("podcast_creator.nodes.asyncio.sleep", new_callable=AsyncMock) as sleep:
        result = asyncio.run(generate_all_audio_node(state, {"configurable": {}}))
    assert result["audio_clips"] == [clips / f"{i:04d}.mp3" for i in range(4)]
    sleep.assert_awaited_once_with(1)
    assert not (clips / "0006.mp3").exists()
    calls = tts.agenerate_multi_speaker_speech.call_args_list
    assert len(calls) == 4
    assert calls[0].kwargs["text"] == format_dialogue(transcript[:2])
    assert calls[0].kwargs["speaker_configs"] == [
        {"speaker": "A", "voice": "voice-A"},
        {"speaker": "B", "voice": "voice-B"},
    ]
    assert calls[0].kwargs["seed"] == 0
    assert calls[0].kwargs["settings"] == {"stability": 0.5}
    assert profile.tts_config["seed"] == 0
    assert all(len(call.kwargs["text"]) <= 2000 for call in calls)


def test_google_single_group(tts, tmp_path):
    data = profile_data()
    data.update(tts_provider="google", tts_model="gemini-2.5-flash-preview-tts")
    profile = SpeakerProfile(**data)
    state = {
        "transcript": turns("ABAB", 900),
        "output_dir": tmp_path,
        "speaker_profile": profile,
    }
    with patch("podcast_creator.nodes.asyncio.sleep", new_callable=AsyncMock) as sleep:
        result = asyncio.run(generate_all_audio_node(state, {"configurable": {}}))
    assert len(result["audio_clips"]) == 1
    tts.agenerate_multi_speaker_speech.assert_awaited_once()
    sleep.assert_not_called()


def test_regeneration_only_selected_group_and_preserves_on_failure(tts, tmp_path):
    profile = SpeakerProfile(
        **profile_data(tts_config={"api_key": "secret", "seed": 7})
    )
    state = {
        "transcript": turns("ABAB", 900),
        "output_dir": tmp_path,
        "speaker_profile": profile,
    }
    asyncio.run(generate_all_audio_node(state, {"configurable": {}}))
    plan_text = (tmp_path / "audio_groups.json").read_text()
    assert "secret" not in plan_text
    clips = tmp_path / "clips"
    first = clips / "0000.mp3"
    second = clips / "0001.mp3"
    first.write_bytes(b"keep first")
    second.write_bytes(b"keep second")
    original_call = tts.agenerate_multi_speaker_speech.call_args_list[1].kwargs["text"]
    tts.agenerate_multi_speaker_speech.reset_mock()
    profile.tts_config["seed"] = 8
    result = asyncio.run(regenerate_audio_group(tmp_path, 1, profile))
    assert result == second
    assert first.read_bytes() == b"keep first"
    assert second.read_bytes() == b"new audio"
    tts.agenerate_multi_speaker_speech.assert_awaited_once()
    assert tts.agenerate_multi_speaker_speech.call_args.kwargs["text"] == original_call
    assert tts.agenerate_multi_speaker_speech.call_args.kwargs["seed"] == 8
    tts.agenerate_multi_speaker_speech.side_effect = ValueError("bad voice")
    with pytest.raises(ValueError, match="bad voice"):
        asyncio.run(regenerate_audio_group(tmp_path, 1, profile))
    assert second.read_bytes() == b"new audio"
    assert (tmp_path / "audio_groups.json").read_text() == plan_text
    with pytest.raises(ValueError, match="outside"):
        asyncio.run(regenerate_audio_group(tmp_path, -1, profile))


def test_group_transient_failure_retries(tts, tmp_path):
    profile = SpeakerProfile(**profile_data())
    write_audio = tts.agenerate_multi_speaker_speech.side_effect
    attempts = 0

    async def fail_then_write(**kwargs):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise RuntimeError("temporary connection failure")
        await write_audio(**kwargs)

    tts.agenerate_multi_speaker_speech.side_effect = fail_then_write
    state = {
        "transcript": turns("AB"),
        "output_dir": tmp_path,
        "speaker_profile": profile,
    }
    with patch("podcast_creator.nodes.asyncio.sleep", new_callable=AsyncMock):
        asyncio.run(generate_all_audio_node(state, {"configurable": {}}))
    assert attempts == 2
