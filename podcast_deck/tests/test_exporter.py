from __future__ import annotations

import json

import pytest

from podcast_deck.exporter import DeckBuildOptions, export_deck
from podcast_deck.schema import DeckSchemaError, parse_deck


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
    assert "deck-debug-highlight" in content
