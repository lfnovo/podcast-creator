"""SRT/timeline alignment adapter for deck narration."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

from .timeline import SlideCue


@dataclass(slots=True)
class AlignmentResult:
    method: str
    cues: list[SlideCue]


_SRT_TIME_RE = re.compile(
    r"(?P<h1>\d{2}):(?P<m1>\d{2}):(?P<s1>\d{2}),(?P<ms1>\d{3})\s*-->\s*"
    r"(?P<h2>\d{2}):(?P<m2>\d{2}):(?P<s2>\d{2}),(?P<ms2>\d{3})"
)


def _to_seconds(h: str, m: str, s: str, ms: str) -> float:
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000.0


def parse_srt_intervals(srt_path: Path) -> list[tuple[float, float]]:
    """Parse SRT intervals as (start_sec, end_sec)."""
    text = srt_path.read_text(encoding="utf-8")
    intervals: list[tuple[float, float]] = []
    for match in _SRT_TIME_RE.finditer(text):
        start = _to_seconds(
            match.group("h1"),
            match.group("m1"),
            match.group("s1"),
            match.group("ms1"),
        )
        end = _to_seconds(
            match.group("h2"),
            match.group("m2"),
            match.group("s2"),
            match.group("ms2"),
        )
        if end < start:
            end = start
        intervals.append((start, end))
    return intervals


def _is_monotonic_non_overlapping(intervals: list[tuple[float, float]]) -> bool:
    if not intervals:
        return True
    prev_start, prev_end = intervals[0]
    for start, end in intervals[1:]:
        if start < prev_start:
            return False
        if start < prev_end:
            return False
        if end < start:
            return False
        prev_start, prev_end = start, end
    return True


def align_with_srt_or_fallback(
    slide_ids: list[str],
    fallback_cues: list[SlideCue],
    srt_path: Path | None = None,
) -> AlignmentResult:
    """
    Use SRT intervals when available, otherwise fallback to computed timeline cues.

    This adapter keeps a stable interface while allowing future aeneas/Whisper
    integration without touching caller code.
    """
    if srt_path is None or not srt_path.exists():
        return AlignmentResult(method="fallback_timeline", cues=fallback_cues)

    try:
        intervals = parse_srt_intervals(srt_path)
    except (OSError, UnicodeDecodeError, ValueError):
        return AlignmentResult(method="fallback_timeline", cues=fallback_cues)
    if not intervals:
        return AlignmentResult(method="fallback_timeline", cues=fallback_cues)
    if len(intervals) != len(slide_ids):
        return AlignmentResult(method="fallback_timeline", cues=fallback_cues)
    if not _is_monotonic_non_overlapping(intervals):
        return AlignmentResult(method="fallback_timeline", cues=fallback_cues)

    # Map intervals to slides by index; overflow intervals are ignored.
    cues: list[SlideCue] = []
    for idx, slide_id in enumerate(slide_ids):
        start, end = intervals[idx]
        cues.append(SlideCue(slide_id=slide_id, start_sec=start, end_sec=end))

    if not cues:
        return AlignmentResult(method="fallback_timeline", cues=fallback_cues)
    return AlignmentResult(method="srt_index_map", cues=cues)
