from __future__ import annotations

from podcast_deck.schema import DeckSlide
from podcast_deck.timeline import allocate_cues


def test_allocate_cues_weighted_chars_sums_to_total() -> None:
    slides = [
        DeckSlide(id="s1", content="短"),
        DeckSlide(id="s2", content="这是更长的一段文本"),
    ]
    cues = allocate_cues(slides, total_duration_sec=12.0, strategy="weighted_chars")
    assert len(cues) == 2
    assert abs(cues[-1].end_sec - 12.0) < 1e-6
    assert cues[1].duration_sec > cues[0].duration_sec


def test_allocate_cues_uniform_even_split() -> None:
    slides = [
        DeckSlide(id="s1", content="a"),
        DeckSlide(id="s2", content="b"),
        DeckSlide(id="s3", content="c"),
    ]
    cues = allocate_cues(slides, total_duration_sec=9.0, strategy="uniform")
    assert len(cues) == 3
    assert abs(cues[0].duration_sec - 3.0) < 1e-6
    assert abs(cues[1].duration_sec - 3.0) < 1e-6
    assert abs(cues[2].duration_sec - 3.0) < 1e-6
