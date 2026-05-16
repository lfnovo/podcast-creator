"""CLI for HTML deck export."""

from __future__ import annotations

from pathlib import Path
import json
import os

import click

from .exporter import DeckBuildOptions, export_deck
from .narration import generate_narration
from .schema import DeckSchemaError, parse_deck


def _normalize_audio_src_for_html(audio_path: Path, html_parent: Path) -> str:
    """
    Build HTML-safe audio src.

    Prefer relative path for portability; if relative mapping is not possible
    (e.g., Windows cross-drive), fall back to file URI.
    """
    try:
        rel = os.path.relpath(audio_path.resolve(), html_parent.resolve())
        return rel.replace("\\", "/")
    except ValueError:
        return audio_path.resolve().as_uri()


@click.group()
def cli() -> None:
    """Podcast deck tools."""


@cli.command("export")
@click.option(
    "--input",
    "input_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    required=True,
    help="Path to deck/outline JSON file.",
)
@click.option(
    "--output",
    "output_path",
    type=click.Path(dir_okay=False, path_type=Path),
    required=True,
    help="Path to output single-file HTML.",
)
@click.option(
    "--debug-script",
    is_flag=True,
    default=False,
    help="Include debug script block in HTML (for local debug builds only).",
)
@click.option(
    "--aspect-ratio",
    type=click.Choice(["16:9", "4:3"], case_sensitive=False),
    default="16:9",
    show_default=True,
    help="Deck aspect ratio.",
)
def export_cmd(
    input_path: Path, output_path: Path, debug_script: bool, aspect_ratio: str
) -> None:
    """Export deck JSON to single-file HTML."""
    try:
        result = export_deck(
            input_path=input_path,
            output_path=output_path,
            options=DeckBuildOptions(
                debug_script_enabled=debug_script, aspect_ratio=aspect_ratio
            ),
        )
        size = result.stat().st_size
        click.echo(f"✅ Deck exported: {result} ({size} bytes)")
    except DeckSchemaError as exc:
        raise click.ClickException(f"Schema validation failed: {exc}") from exc
    except Exception as exc:  # pragma: no cover - defensive boundary
        raise click.ClickException(str(exc)) from exc


@cli.command("narrate")
@click.option(
    "--input",
    "input_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    required=True,
    help="Path to deck JSON file.",
)
@click.option(
    "--output-html",
    "output_html",
    type=click.Path(dir_okay=False, path_type=Path),
    required=True,
    help="Path to output narrated HTML.",
)
@click.option(
    "--workspace",
    type=click.Path(file_okay=False, path_type=Path),
    default=Path("output/decks/narration"),
    show_default=True,
    help="Workspace directory for clips/audio/intermediate files.",
)
@click.option(
    "--tts-provider",
    default="edge_tts",
    show_default=True,
    help="TTS provider name (default: edge_tts).",
)
@click.option(
    "--tts-model",
    default="edge-1",
    show_default=True,
    help="TTS model label passed to provider factory.",
)
@click.option(
    "--voice",
    default=None,
    help="Voice id/name for TTS provider.",
)
@click.option(
    "--speaking-rate",
    default=1.0,
    type=click.FloatRange(min=0.0, min_open=True),
    show_default=True,
    help="Speaking rate multiplier for TTS.",
)
@click.option(
    "--timeline-strategy",
    type=click.Choice(["weighted_chars", "uniform"], case_sensitive=False),
    default="weighted_chars",
    show_default=True,
    help="Fallback timeline allocation strategy.",
)
@click.option(
    "--srt",
    "srt_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    default=None,
    help="Optional SRT file for alignment adapter.",
)
@click.option(
    "--audio-autoplay/--no-audio-autoplay",
    default=False,
    show_default=True,
    help="Whether HTML audio should autoplay.",
)
def narrate_cmd(
    input_path: Path,
    output_html: Path,
    workspace: Path,
    tts_provider: str,
    tts_model: str,
    voice: str | None,
    speaking_rate: float,
    timeline_strategy: str,
    srt_path: Path | None,
    audio_autoplay: bool,
) -> None:
    """Generate per-slide narration and export auto-paging narrated HTML."""
    try:
        payload = json.loads(input_path.read_text(encoding="utf-8"))
        document = parse_deck(payload)
        artifacts = generate_narration(
            document=document,
            workspace=workspace,
            provider=tts_provider,
            model=tts_model,
            voice=voice,
            speaking_rate=speaking_rate,
            timeline_strategy=timeline_strategy,
            srt_path=srt_path,
        )

        output_html.parent.mkdir(parents=True, exist_ok=True)
        audio_src = _normalize_audio_src_for_html(
            artifacts.audio_path, output_html.parent
        )
        result = export_deck(
            input_path=artifacts.updated_json_path,
            output_path=output_html,
            options=DeckBuildOptions(
                audio_src=audio_src,
                timeline_cues=artifacts.cues,
                audio_autoplay=audio_autoplay,
            ),
        )
        click.echo(f"✅ Narrated deck exported: {result}")
        click.echo(f"🎧 Narration audio: {artifacts.audio_path}")
        click.echo(
            f"🕒 Alignment method: {artifacts.alignment.method}, cues: {len(artifacts.cues)}"
        )
        click.echo(f"📝 Backfilled JSON: {artifacts.updated_json_path}")
    except DeckSchemaError as exc:
        raise click.ClickException(f"Schema validation failed: {exc}") from exc
    except Exception as exc:  # pragma: no cover - defensive boundary
        raise click.ClickException(str(exc)) from exc


def main() -> None:
    """Console entry for module execution."""
    cli()
