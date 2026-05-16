"""Timeline allocation for auto-paging deck playback."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .schema import DeckSlide


@dataclass(slots=True)
class SlideCue:
    slide_id: str
    start_sec: float
    end_sec: float

    @property
    def duration_sec(self) -> float:
        return max(0.0, self.end_sec - self.start_sec)


def _content_weight(slide: DeckSlide) -> int:
    lines = slide.normalized_content_lines()
    text = "".join(lines).strip()
    if not text:
        return 1
    return max(1, len(text))


def allocate_cues(
    slides: Iterable[DeckSlide],
    total_duration_sec: float,
    strategy: str = "weighted_chars",
) -> list[SlideCue]:
    """Allocate slide cues by total duration with char-weighted strategy."""
    slide_list = list(slides)
    if not slide_list:
        return []
    duration = max(0.0, float(total_duration_sec))
    if duration <= 0.0:
        return [
            SlideCue(slide_id=s.id, start_sec=0.0, end_sec=0.0)
            for s in slide_list
        ]

    if strategy not in {"uniform", "weighted_chars"}:
        raise ValueError(f"Unsupported timeline strategy: {strategy}")

    if strategy == "uniform":
        weights = [1 for _ in slide_list]
    else:
        weights = [_content_weight(s) for s in slide_list]

    weight_sum = float(sum(weights)) or float(len(weights))
    raw = [duration * (w / weight_sum) for w in weights]

    # Prefer explicit duration hints where available.
    hinted_total = 0.0
    hinted_indexes: list[int] = []
    for idx, s in enumerate(slide_list):
        if s.duration_hint_sec is not None and s.duration_hint_sec > 0:
            raw[idx] = float(s.duration_hint_sec)
            hinted_indexes.append(idx)
            hinted_total += raw[idx]

    if hinted_indexes and hinted_total < duration:
        free_indexes = [i for i in range(len(slide_list)) if i not in hinted_indexes]
        if free_indexes:
            free_sum = sum(raw[i] for i in free_indexes) or float(len(free_indexes))
            remaining = duration - hinted_total
            for i in free_indexes:
                raw[i] = remaining * (raw[i] / free_sum)

    # Numeric stability: keep exact total by adjusting tail.
    total_now = sum(raw)
    if raw and total_now > 0:
        raw[-1] += duration - total_now
        raw[-1] = max(0.0, raw[-1])

    cues: list[SlideCue] = []
    start = 0.0
    for i, slide in enumerate(slide_list):
        end = start + raw[i]
        if i == len(slide_list) - 1:
            end = duration
        cues.append(
            SlideCue(slide_id=slide.id, start_sec=start, end_sec=max(start, end))
        )
        start = end
    return cues
