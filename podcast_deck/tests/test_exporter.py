from __future__ import annotations

import json

import pytest

from podcast_deck.cli import _normalize_audio_src_for_html
from podcast_deck.exporter import DECK_DEBUG_MARKERS, DeckBuildOptions, export_deck
from podcast_deck.schema import DeckSchemaError, parse_deck
from podcast_deck.timeline import SlideCue


def _sample_payload() -> dict:
    return {
        "schemaVersion": "1.0",
        "meta": {"title": "Deck Demo", "lang": "zh-CN"},
        "slides": [
            {"id": "s1", "content": ["第一点", "第二点"]},
            {"id": "s2", "content": "结论页"},
        ],
    }


def test_parse_deck_validates_required_fields() -> None:
    payload = _sample_payload()
    deck = parse_deck(payload)
    assert deck.meta.title == "Deck Demo"
    assert len(deck.slides) == 2


def test_parse_deck_raises_for_bad_schema_version() -> None:
    payload = _sample_payload()
    payload["schemaVersion"] = "2.0"
    with pytest.raises(DeckSchemaError):
        parse_deck(payload)


def test_export_deck_generates_single_html(tmp_path) -> None:
    input_file = tmp_path / "outline.json"
    output_file = tmp_path / "deck.html"
    input_file.write_text(
        json.dumps(_sample_payload(), ensure_ascii=False), encoding="utf-8"
    )

    export_deck(
        input_path=input_file,
        output_path=output_file,
        options=DeckBuildOptions(debug_script_enabled=False),
    )

    content = output_file.read_text(encoding="utf-8")
    assert "<html lang=\"zh-CN\">" in content
    assert "deck-slide" in content
    assert "ArrowRight" in content
    assert "display: flex !important;" in content
    assert output_file.stat().st_size < 100 * 1024
    for marker in DECK_DEBUG_MARKERS:
        assert marker not in content


def test_export_deck_with_debug_script_includes_markers(tmp_path) -> None:
    input_file = tmp_path / "outline.json"
    output_file = tmp_path / "deck.debug.html"
    input_file.write_text(
        json.dumps(_sample_payload(), ensure_ascii=False), encoding="utf-8"
    )

    export_deck(
        input_path=input_file,
        output_path=output_file,
        options=DeckBuildOptions(debug_script_enabled=True),
    )
    content = output_file.read_text(encoding="utf-8")
    for marker in DECK_DEBUG_MARKERS:
        assert marker in content


def test_export_deck_with_audio_and_timeline(tmp_path) -> None:
    input_file = tmp_path / "outline.json"
    output_file = tmp_path / "deck.audio.html"
    input_file.write_text(
        json.dumps(_sample_payload(), ensure_ascii=False), encoding="utf-8"
    )
    cues = [
        SlideCue(slide_id="s1", start_sec=0.0, end_sec=2.0),
        SlideCue(slide_id="s2", start_sec=2.0, end_sec=4.0),
    ]
    export_deck(
        input_path=input_file,
        output_path=output_file,
        options=DeckBuildOptions(
            audio_src="narration.mp3",
            timeline_cues=cues,
            audio_autoplay=True,
        ),
    )
    content = output_file.read_text(encoding="utf-8")
    assert "id=\"deck-audio\"" in content
    assert "narration.mp3" in content
    assert "const cues =" in content
    assert "aria-live" in content


def test_export_deck_timeline_json_escapes_script_context(tmp_path) -> None:
    payload = _sample_payload()
    payload["slides"][0]["id"] = "s1</script><img src=x onerror=alert(1)>"
    input_file = tmp_path / "outline.json"
    output_file = tmp_path / "deck.audio.html"
    input_file.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    cues = [
        SlideCue(slide_id=payload["slides"][0]["id"], start_sec=0.0, end_sec=2.0),
        SlideCue(slide_id="s2", start_sec=2.0, end_sec=4.0),
    ]

    export_deck(
        input_path=input_file,
        output_path=output_file,
        options=DeckBuildOptions(audio_src="narration.mp3", timeline_cues=cues),
    )
    content = output_file.read_text(encoding="utf-8")
    assert "\\u003C/script\\u003E" in content


@pytest.mark.parametrize(
    "duration_hint",
    [True, -0.1, float("nan"), float("inf")],
)
def test_parse_deck_rejects_invalid_duration_hint(duration_hint) -> None:
    payload = _sample_payload()
    payload["slides"][0]["durationHintSec"] = duration_hint
    with pytest.raises(DeckSchemaError):
        parse_deck(payload)


def test_parse_deck_rejects_bool_transition_budget() -> None:
    payload = _sample_payload()
    payload["slides"][0]["transitionBudgetMs"] = False
    with pytest.raises(DeckSchemaError):
        parse_deck(payload)


def test_parse_deck_rejects_duplicate_slide_ids() -> None:
    payload = _sample_payload()
    payload["slides"][1]["id"] = payload["slides"][0]["id"]
    with pytest.raises(DeckSchemaError):
        parse_deck(payload)


def test_normalize_audio_src_for_html_encodes_reserved_chars(tmp_path) -> None:
    html_parent = tmp_path / "html"
    audio_parent = tmp_path / "audio"
    html_parent.mkdir(parents=True, exist_ok=True)
    audio_parent.mkdir(parents=True, exist_ok=True)
    audio_path = audio_parent / "narration #1?.mp3"
    audio_path.write_bytes(b"demo")
    src = _normalize_audio_src_for_html(audio_path, html_parent)
    assert "%23" in src
    assert "%3F" in src
    assert " " not in src


@pytest.mark.parametrize("bad_content", [123, {"x": "y"}, [1, "ok"]])
def test_parse_deck_rejects_invalid_content_type(bad_content) -> None:
    payload = _sample_payload()
    payload["slides"][0]["content"] = bad_content
    with pytest.raises(DeckSchemaError):
        parse_deck(payload)
