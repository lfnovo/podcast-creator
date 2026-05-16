"""Narration pipeline for deck slides."""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from pathlib import Path
import sys
from typing import Any

from pydub import AudioSegment

try:
    from podcast_creator.voices.factory import build_tts
except ModuleNotFoundError:  # pragma: no cover - local source fallback
    repo_src = Path(__file__).resolve().parents[1] / "src"
    if str(repo_src) not in sys.path:
        sys.path.insert(0, str(repo_src))
    from podcast_creator.voices.factory import build_tts

from .alignment import AlignmentResult, align_with_srt_or_fallback
from .schema import DeckDocument
from .timeline import SlideCue, allocate_cues


@dataclass(slots=True)
class NarrationArtifacts:
    audio_path: Path
    cues: list[SlideCue]
    alignment: AlignmentResult
    updated_json_path: Path


def _slide_text_for_tts(slide_content_lines: list[str]) -> str:
    text = "。".join(line.strip() for line in slide_content_lines if line.strip())
    return text.strip() or "空白页。"


def _audio_duration_seconds(path: Path) -> float:
    seg = AudioSegment.from_file(path)
    return max(0.0, len(seg) / 1000.0)


async def _synthesize_slide_audio_async(
    document: DeckDocument,
    audio_dir: Path,
    provider: str,
    model: str,
    voice: str | None,
    speaking_rate: float,
    tts_config: dict[str, Any] | None = None,
) -> list[tuple[Path, float]]:
    tts = build_tts(
        provider=provider,
        model=model,
        config=tts_config or {},
    )
    outputs: list[tuple[Path, float]] = []
    for i, slide in enumerate(document.slides):
        text = _slide_text_for_tts(slide.normalized_content_lines())
        clip_path = audio_dir / f"slide_{i:03d}.mp3"
        await tts.synthesize(
            text=text,
            output_path=clip_path,
            voice=voice,
            speaking_rate=speaking_rate,
        )
        outputs.append((clip_path, _audio_duration_seconds(clip_path)))
    return outputs


def _write_updated_json(
    document: DeckDocument, cues: list[SlideCue], output_path: Path
) -> Path:
    cue_map = {cue.slide_id: cue.duration_sec for cue in cues}
    payload = {
        "schemaVersion": document.schema_version,
        "meta": {
            "title": document.meta.title,
            "description": document.meta.description,
            "lang": document.meta.lang,
        },
        "slides": [],
    }
    for slide in document.slides:
        item = {
            "id": slide.id,
            "layout": slide.layout,
            "content": slide.content,
            "durationHintSec": round(cue_map.get(slide.id, 0.0), 3),
            "syncHints": slide.sync_hints,
            "transitionBudgetMs": slide.transition_budget_ms,
        }
        payload["slides"].append(item)
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return output_path


def generate_narration(
    document: DeckDocument,
    workspace: Path,
    provider: str = "edge_tts",
    model: str = "edge-1",
    voice: str | None = None,
    speaking_rate: float = 1.0,
    timeline_strategy: str = "weighted_chars",
    tts_config: dict[str, Any] | None = None,
    srt_path: Path | None = None,
) -> NarrationArtifacts:
    """Generate per-slide narration, merged audio, and timeline cues."""
    workspace.mkdir(parents=True, exist_ok=True)
    clips_dir = workspace / "clips"
    clips_dir.mkdir(parents=True, exist_ok=True)

    clips = asyncio.run(
        _synthesize_slide_audio_async(
            document=document,
            audio_dir=clips_dir,
            provider=provider,
            model=model,
            voice=voice,
            speaking_rate=speaking_rate,
            tts_config=tts_config,
        )
    )

    merged = AudioSegment.silent(duration=0)
    total_duration = 0.0
    for clip_path, duration in clips:
        merged += AudioSegment.from_file(clip_path)
        total_duration += duration
    audio_path = workspace / "narration.mp3"
    merged.export(audio_path, format="mp3")

    fallback_cues = allocate_cues(
        slides=document.slides,
        total_duration_sec=total_duration,
        strategy=timeline_strategy,
    )
    alignment = align_with_srt_or_fallback(
        slide_ids=[s.id for s in document.slides],
        fallback_cues=fallback_cues,
        srt_path=srt_path,
    )
    updated_json = _write_updated_json(
        document=document,
        cues=alignment.cues,
        output_path=workspace / "deck.with_duration.json",
    )
    return NarrationArtifacts(
        audio_path=audio_path,
        cues=alignment.cues,
        alignment=alignment,
        updated_json_path=updated_json,
    )
