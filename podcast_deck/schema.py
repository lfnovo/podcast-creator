"""Schema validation for Deck JSON v1.0."""

from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Any


class DeckSchemaError(ValueError):
    """Raised when deck input does not satisfy schema requirements."""


@dataclass(slots=True)
class DeckMeta:
    title: str
    description: str = ""
    lang: str = "zh-CN"


@dataclass(slots=True)
class DeckSlide:
    id: str
    layout: str = "content"
    content: str | list[Any] = ""
    duration_hint_sec: float | None = None
    sync_hints: dict[str, Any] = field(default_factory=dict)
    transition_budget_ms: int = 0

    def normalized_content_lines(self) -> list[str]:
        """Return content as line array for rendering."""
        if isinstance(self.content, str):
            lines = [line.strip() for line in self.content.splitlines() if line.strip()]
            return lines or [""]
        if isinstance(self.content, list):
            result: list[str] = []
            for item in self.content:
                if isinstance(item, str):
                    text = item.strip()
                    if text:
                        result.append(text)
                else:
                    result.append(str(item))
            return result or [""]
        return [str(self.content)]


@dataclass(slots=True)
class DeckDocument:
    schema_version: str
    meta: DeckMeta
    slides: list[DeckSlide]


def _as_dict(value: Any, *, field_name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise DeckSchemaError(f"`{field_name}` must be an object")
    return value


def _as_non_empty_str(value: Any, *, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise DeckSchemaError(f"`{field_name}` must be a non-empty string")
    return value.strip()


def _as_optional_number(value: Any, *, field_name: str) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool):
        raise DeckSchemaError(f"`{field_name}` must be a number when provided")
    if isinstance(value, (int, float)):
        parsed = float(value)
        if not math.isfinite(parsed):
            raise DeckSchemaError(f"`{field_name}` must be a finite number")
        if parsed < 0:
            raise DeckSchemaError(f"`{field_name}` must be >= 0")
        return parsed
    raise DeckSchemaError(f"`{field_name}` must be a number when provided")


def _as_optional_int(value: Any, *, field_name: str, default: int = 0) -> int:
    if value is None:
        return default
    if isinstance(value, bool):
        raise DeckSchemaError(f"`{field_name}` must be an integer when provided")
    if isinstance(value, int):
        if value < 0:
            raise DeckSchemaError(f"`{field_name}` must be >= 0")
        return value
    if isinstance(value, float) and value.is_integer():
        parsed = int(value)
        if parsed < 0:
            raise DeckSchemaError(f"`{field_name}` must be >= 0")
        return parsed
    raise DeckSchemaError(f"`{field_name}` must be an integer when provided")


def parse_deck(data: dict[str, Any]) -> DeckDocument:
    """Parse and validate Deck JSON into typed structure."""
    payload = _as_dict(data, field_name="root")

    schema_version = _as_non_empty_str(
        payload.get("schemaVersion"), field_name="schemaVersion"
    )
    if schema_version != "1.0":
        raise DeckSchemaError(
            f"Unsupported schemaVersion `{schema_version}`, expected `1.0`"
        )

    meta_dict = _as_dict(payload.get("meta"), field_name="meta")
    meta = DeckMeta(
        title=_as_non_empty_str(meta_dict.get("title"), field_name="meta.title"),
        description=str(meta_dict.get("description", "") or ""),
        lang=str(meta_dict.get("lang", "zh-CN") or "zh-CN"),
    )

    slides_raw = payload.get("slides")
    if not isinstance(slides_raw, list) or not slides_raw:
        raise DeckSchemaError("`slides` must be a non-empty array")

    slides: list[DeckSlide] = []
    for index, raw_slide in enumerate(slides_raw):
        item = _as_dict(raw_slide, field_name=f"slides[{index}]")
        slide = DeckSlide(
            id=_as_non_empty_str(item.get("id"), field_name=f"slides[{index}].id"),
            layout=str(item.get("layout", "content") or "content"),
            content=item.get("content", ""),
            duration_hint_sec=_as_optional_number(
                item.get("durationHintSec"), field_name=f"slides[{index}].durationHintSec"
            ),
            sync_hints=_as_dict(item.get("syncHints", {}), field_name=f"slides[{index}].syncHints"),
            transition_budget_ms=_as_optional_int(
                item.get("transitionBudgetMs"),
                field_name=f"slides[{index}].transitionBudgetMs",
                default=0,
            ),
        )
        slides.append(slide)

    return DeckDocument(schema_version=schema_version, meta=meta, slides=slides)
