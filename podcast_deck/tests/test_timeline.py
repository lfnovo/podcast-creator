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


def test_allocate_cues_oversized_duration_hints_are_normalized() -> None:
    slides = [
        DeckSlide(id="s1", content="a", duration_hint_sec=10.0),
        DeckSlide(id="s2", content="b", duration_hint_sec=10.0),
        DeckSlide(id="s3", content="c"),
    ]
    cues = allocate_cues(slides, total_duration_sec=12.0, strategy="weighted_chars")
    assert len(cues) == 3
    assert cues[0].start_sec == 0.0
    assert cues[-1].end_sec == 12.0
    assert all(cue.end_sec >= cue.start_sec for cue in cues)
    assert all(0.0 <= cue.start_sec <= 12.0 for cue in cues)
    assert all(0.0 <= cue.end_sec <= 12.0 for cue in cues)
    # Hinted slides should still dominate non-hinted duration after normalization.
    assert cues[0].duration_sec > cues[2].duration_sec
    assert cues[1].duration_sec > cues[2].duration_sec
    assert abs(cues[0].duration_sec - cues[1].duration_sec) < 1e-6
