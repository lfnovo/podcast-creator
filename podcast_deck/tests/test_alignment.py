from __future__ import annotations

from pathlib import Path

from podcast_deck.alignment import align_with_srt_or_fallback, parse_srt_intervals
from podcast_deck.timeline import SlideCue


def test_parse_srt_intervals(tmp_path: Path) -> None:
    srt = tmp_path / "sample.srt"
    srt.write_text(
        "\n".join(
            [
                "1",
                "00:00:00,000 --> 00:00:02,500",
                "hello",
                "",
                "2",
                "00:00:02,500 --> 00:00:05,000",
                "world",
            ]
        ),
        encoding="utf-8",
    )
    intervals = parse_srt_intervals(srt)
    assert len(intervals) == 2
    assert intervals[0] == (0.0, 2.5)
    assert intervals[1] == (2.5, 5.0)


def test_align_with_srt_or_fallback_uses_fallback_when_missing() -> None:
    fallback = [
        SlideCue(slide_id="s1", start_sec=0.0, end_sec=1.0),
        SlideCue(slide_id="s2", start_sec=1.0, end_sec=2.0),
    ]
    result = align_with_srt_or_fallback(["s1", "s2"], fallback, srt_path=None)
    assert result.method == "fallback_timeline"
    assert result.cues == fallback


def test_align_with_srt_or_fallback_uses_fallback_when_srt_partial(
    tmp_path: Path,
) -> None:
    fallback = [
        SlideCue(slide_id="s1", start_sec=0.0, end_sec=1.0),
        SlideCue(slide_id="s2", start_sec=1.0, end_sec=2.0),
        SlideCue(slide_id="s3", start_sec=2.0, end_sec=3.0),
    ]
    srt = tmp_path / "partial.srt"
    srt.write_text(
        "\n".join(
            [
                "1",
                "00:00:00,000 --> 00:00:01,500",
                "only one interval",
            ]
        ),
        encoding="utf-8",
    )

    result = align_with_srt_or_fallback(["s1", "s2", "s3"], fallback, srt_path=srt)
    assert result.method == "fallback_timeline"
    assert result.cues == fallback


def test_align_with_srt_or_fallback_uses_fallback_when_srt_unreadable(
    tmp_path: Path,
) -> None:
    fallback = [SlideCue(slide_id="s1", start_sec=0.0, end_sec=1.0)]
    srt = tmp_path / "broken.srt"
    srt.write_bytes(b"\xff\xfe\x00\x00")
    result = align_with_srt_or_fallback(["s1"], fallback, srt_path=srt)
    assert result.method == "fallback_timeline"
    assert result.cues == fallback
