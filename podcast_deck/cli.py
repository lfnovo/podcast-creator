"""CLI for HTML deck export."""

from __future__ import annotations

from pathlib import Path
import json
import os
import shutil
from urllib.parse import quote

import click

from .exporter import DeckBuildOptions, export_deck
from .frame_capture import FrameCaptureOptions, capture_frame_sequence
from .narration import generate_narration
from .render_video import RenderVideoOptions, render_video_from_frames
from .schema import DeckSchemaError, parse_deck


def _normalize_audio_src_for_html(audio_path: Path, html_parent: Path) -> str:
    """
    Build HTML-safe audio src.

    Prefer relative path for portability; if relative mapping is not possible
    (e.g., Windows cross-drive), fall back to file URI.
    """
    try:
        rel = os.path.relpath(audio_path.resolve(), html_parent.resolve())
        rel_url = rel.replace("\\", "/")
        return quote(rel_url, safe="/._-~")
    except ValueError:
        return audio_path.resolve().as_uri()


def _cleanup_synth_workspace(
    workspace: Path,
    *,
    remove_generated_subtitle: Path | None = None,
) -> None:
    cleanup_targets = [
        workspace / "frames",
        workspace / "slides",
        workspace / "frame_manifest.json",
    ]
    if remove_generated_subtitle is not None:
        cleanup_targets.append(remove_generated_subtitle)

    for target in cleanup_targets:
        if target.is_dir():
            shutil.rmtree(target, ignore_errors=True)
        elif target.exists():
            target.unlink(missing_ok=True)


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


@cli.command("capture-frames")
@click.option(
    "--input",
    "input_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    required=True,
    help="Path to deck JSON file.",
)
@click.option(
    "--workspace",
    type=click.Path(file_okay=False, path_type=Path),
    default=Path("output/decks/frames"),
    show_default=True,
    help="Workspace directory for captured slides/frames/manifest.",
)
@click.option("--fps", default=30, type=click.IntRange(min=1), show_default=True)
@click.option(
    "--width",
    default=1280,
    type=click.IntRange(min=320),
    show_default=True,
    help="Frame width in px.",
)
@click.option(
    "--height",
    default=720,
    type=click.IntRange(min=240),
    show_default=True,
    help="Frame height in px.",
)
@click.option(
    "--hold-sec",
    default=2.0,
    type=click.FloatRange(min=0.0, min_open=True),
    show_default=True,
    help="Per-slide hold duration in seconds.",
)
@click.option(
    "--transition-sec",
    default=0.6,
    type=click.FloatRange(min=0.0),
    show_default=True,
    help="Per-gap transition duration in seconds.",
)
def capture_frames_cmd(
    input_path: Path,
    workspace: Path,
    fps: int,
    width: int,
    height: int,
    hold_sec: float,
    transition_sec: float,
) -> None:
    """Capture headless hold/transition frame sequence for P3 video stage."""
    try:
        artifacts = capture_frame_sequence(
            input_json_path=input_path,
            workspace=workspace,
            options=FrameCaptureOptions(
                width=width,
                height=height,
                fps=fps,
                hold_sec=hold_sec,
                transition_sec=transition_sec,
            ),
        )
        click.echo(f"✅ Captured frames: {artifacts.total_frames}")
        click.echo(f"🖼️ Frame dir: {artifacts.frame_dir}")
        click.echo(f"📄 Manifest: {artifacts.manifest_path}")
        click.echo(
            "ℹ️ Breakdown: "
            f"hold={artifacts.hold_frames_per_slide}, "
            f"transition={artifacts.transition_frames_per_gap}"
        )
    except DeckSchemaError as exc:
        raise click.ClickException(f"Schema validation failed: {exc}") from exc
    except Exception as exc:  # pragma: no cover - defensive boundary
        raise click.ClickException(str(exc)) from exc


@cli.command("render-video")
@click.option(
    "--workspace",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    required=True,
    help="Workspace directory containing frame_manifest.json and frames/.",
)
@click.option(
    "--output-mp4",
    "output_mp4",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    help="Output MP4 path (default: <workspace>/deck.mp4).",
)
@click.option(
    "--fps",
    default=None,
    type=click.IntRange(min=1),
    help="Override FPS from manifest.",
)
@click.option("--crf", default=18, type=click.IntRange(min=0, max=51), show_default=True)
@click.option(
    "--preset",
    default="medium",
    type=click.Choice(
        [
            "ultrafast",
            "superfast",
            "veryfast",
            "faster",
            "fast",
            "medium",
            "slow",
            "slower",
            "veryslow",
        ],
        case_sensitive=False,
    ),
    show_default=True,
)
@click.option(
    "--ffmpeg-path",
    default="ffmpeg",
    show_default=True,
    help="Path to ffmpeg binary.",
)
@click.option(
    "--subtitle-mode",
    type=click.Choice(["none", "burn"], case_sensitive=False),
    default="none",
    show_default=True,
    help="Subtitle mode for rendered MP4.",
)
@click.option(
    "--subtitle-srt",
    "subtitle_srt",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    help="Optional external SRT path. If omitted in burn mode, generate from manifest.",
)
@click.option(
    "--subtitle-font-size",
    default=28,
    type=click.IntRange(min=8),
    show_default=True,
)
@click.option(
    "--subtitle-margin-v",
    default=36,
    type=click.IntRange(min=0),
    show_default=True,
)
@click.option(
    "--subtitle-alignment",
    default=2,
    type=click.IntRange(min=1, max=9),
    show_default=True,
)
@click.option(
    "--audio",
    "audio_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    default=None,
    help="Optional narration audio path for muxing into MP4.",
)
@click.option(
    "--audio-codec",
    default="aac",
    show_default=True,
    help="Audio codec used when muxing external audio.",
)
@click.option(
    "--audio-bitrate",
    default="192k",
    show_default=True,
    help="Audio bitrate used when muxing external audio.",
)
@click.option(
    "--audio-shortest/--no-audio-shortest",
    default=True,
    show_default=True,
    help="Stop at the shortest stream when muxing audio/video.",
)
def render_video_cmd(
    workspace: Path,
    output_mp4: Path | None,
    fps: int | None,
    crf: int,
    preset: str,
    ffmpeg_path: str,
    subtitle_mode: str,
    subtitle_srt: Path | None,
    subtitle_font_size: int,
    subtitle_margin_v: int,
    subtitle_alignment: int,
    audio_path: Path | None,
    audio_codec: str,
    audio_bitrate: str,
    audio_shortest: bool,
) -> None:
    """Render MP4 from captured frame sequence."""
    try:
        artifacts = render_video_from_frames(
            workspace=workspace,
            output_mp4=output_mp4,
            options=RenderVideoOptions(
                fps=fps,
                crf=crf,
                preset=preset,
                ffmpeg_path=ffmpeg_path,
                subtitle_mode=subtitle_mode,
                subtitle_srt_path=subtitle_srt,
                subtitle_font_size=subtitle_font_size,
                subtitle_margin_v=subtitle_margin_v,
                subtitle_alignment=subtitle_alignment,
                audio_path=audio_path,
                audio_codec=audio_codec,
                audio_bitrate=audio_bitrate,
                audio_shortest=audio_shortest,
            ),
        )
        click.echo(f"✅ Rendered MP4: {artifacts.output_mp4}")
        click.echo(f"🎞️ Frames: {artifacts.frame_count}, fps={artifacts.fps}")
        if artifacts.subtitle_srt_path is not None:
            click.echo(f"📝 Subtitles: {artifacts.subtitle_srt_path}")
        if artifacts.audio_path is not None:
            click.echo(f"🔊 Audio: {artifacts.audio_path}")
    except Exception as exc:  # pragma: no cover - CLI boundary
        raise click.ClickException(str(exc)) from exc


@cli.command("synth-video")
@click.option(
    "--input",
    "input_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    required=True,
    help="Path to deck JSON file.",
)
@click.option(
    "--workspace",
    type=click.Path(file_okay=False, path_type=Path),
    default=Path("output/decks/synth"),
    show_default=True,
    help="Workspace for frames/manifest/subtitles and output video.",
)
@click.option("--fps", default=30, type=click.IntRange(min=1), show_default=True)
@click.option("--width", default=1280, type=click.IntRange(min=320), show_default=True)
@click.option("--height", default=720, type=click.IntRange(min=240), show_default=True)
@click.option(
    "--hold-sec",
    default=2.0,
    type=click.FloatRange(min=0.0, min_open=True),
    show_default=True,
)
@click.option(
    "--transition-sec",
    default=0.6,
    type=click.FloatRange(min=0.0),
    show_default=True,
)
@click.option(
    "--output-mp4",
    "output_mp4",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    help="Output MP4 path (default: <workspace>/deck.mp4).",
)
@click.option("--crf", default=18, type=click.IntRange(min=0, max=51), show_default=True)
@click.option(
    "--preset",
    default="medium",
    type=click.Choice(
        [
            "ultrafast",
            "superfast",
            "veryfast",
            "faster",
            "fast",
            "medium",
            "slow",
            "slower",
            "veryslow",
        ],
        case_sensitive=False,
    ),
    show_default=True,
)
@click.option("--ffmpeg-path", default="ffmpeg", show_default=True)
@click.option(
    "--subtitle-mode",
    type=click.Choice(["none", "burn"], case_sensitive=False),
    default="none",
    show_default=True,
)
@click.option(
    "--subtitle-srt",
    "subtitle_srt",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
)
@click.option(
    "--subtitle-font-size",
    default=28,
    type=click.IntRange(min=8),
    show_default=True,
)
@click.option(
    "--subtitle-margin-v",
    default=36,
    type=click.IntRange(min=0),
    show_default=True,
)
@click.option(
    "--subtitle-alignment",
    default=2,
    type=click.IntRange(min=1, max=9),
    show_default=True,
)
@click.option(
    "--audio",
    "audio_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    default=None,
    help="Optional narration audio path for muxing into MP4.",
)
@click.option("--audio-codec", default="aac", show_default=True)
@click.option("--audio-bitrate", default="192k", show_default=True)
@click.option(
    "--audio-shortest/--no-audio-shortest",
    default=True,
    show_default=True,
)
@click.option(
    "--keep-frames/--clean-workspace",
    default=True,
    show_default=True,
    help="Keep intermediate frames/manifest (or clean them after render).",
)
def synth_video_cmd(
    input_path: Path,
    workspace: Path,
    fps: int,
    width: int,
    height: int,
    hold_sec: float,
    transition_sec: float,
    output_mp4: Path | None,
    crf: int,
    preset: str,
    ffmpeg_path: str,
    subtitle_mode: str,
    subtitle_srt: Path | None,
    subtitle_font_size: int,
    subtitle_margin_v: int,
    subtitle_alignment: int,
    audio_path: Path | None,
    audio_codec: str,
    audio_bitrate: str,
    audio_shortest: bool,
    keep_frames: bool,
) -> None:
    """Capture frames then render final MP4 in one command."""
    try:
        capture_artifacts = capture_frame_sequence(
            input_json_path=input_path,
            workspace=workspace,
            options=FrameCaptureOptions(
                width=width,
                height=height,
                fps=fps,
                hold_sec=hold_sec,
                transition_sec=transition_sec,
            ),
        )
        click.echo(f"✅ Captured frames: {capture_artifacts.total_frames}")
        click.echo(f"📄 Manifest: {capture_artifacts.manifest_path}")

        render_artifacts = render_video_from_frames(
            workspace=workspace,
            output_mp4=output_mp4,
            options=RenderVideoOptions(
                fps=fps,
                crf=crf,
                preset=preset,
                ffmpeg_path=ffmpeg_path,
                subtitle_mode=subtitle_mode,
                subtitle_srt_path=subtitle_srt,
                subtitle_font_size=subtitle_font_size,
                subtitle_margin_v=subtitle_margin_v,
                subtitle_alignment=subtitle_alignment,
                audio_path=audio_path,
                audio_codec=audio_codec,
                audio_bitrate=audio_bitrate,
                audio_shortest=audio_shortest,
            ),
        )
        click.echo(f"✅ Rendered MP4: {render_artifacts.output_mp4}")
        click.echo(f"🎞️ Frames: {render_artifacts.frame_count}, fps={render_artifacts.fps}")
        if render_artifacts.subtitle_srt_path is not None:
            click.echo(f"📝 Subtitles: {render_artifacts.subtitle_srt_path}")
        if render_artifacts.audio_path is not None:
            click.echo(f"🔊 Audio: {render_artifacts.audio_path}")
        if not keep_frames:
            generated_subtitle: Path | None = None
            if subtitle_mode == "burn" and subtitle_srt is None:
                generated_subtitle = render_artifacts.subtitle_srt_path
            _cleanup_synth_workspace(
                workspace,
                remove_generated_subtitle=generated_subtitle,
            )
            click.echo("🧹 Cleaned workspace intermediates (frames/slides/manifest)")
    except DeckSchemaError as exc:
        raise click.ClickException(f"Schema validation failed: {exc}") from exc
    except Exception as exc:  # pragma: no cover - CLI boundary
        raise click.ClickException(str(exc)) from exc


def main() -> None:
    """Console entry for module execution."""
    cli()
