"""Video rendering pipeline from captured frame sequence."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import subprocess


@dataclass(slots=True)
class RenderVideoOptions:
    fps: int | None = None
    crf: int = 18
    preset: str = "medium"
    ffmpeg_path: str = "ffmpeg"
    subtitle_mode: str = "none"  # none | burn
    subtitle_srt_path: Path | None = None
    subtitle_font_size: int = 28
    subtitle_margin_v: int = 36
    subtitle_alignment: int = 2
    audio_path: Path | None = None
    audio_codec: str = "aac"
    audio_bitrate: str = "192k"
    audio_shortest: bool = True


@dataclass(slots=True)
class RenderVideoArtifacts:
    output_mp4: Path
    frame_count: int
    fps: int
    command: list[str]
    subtitle_srt_path: Path | None = None
    audio_path: Path | None = None


def _load_manifest(manifest_path: Path) -> dict:
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def _build_ffmpeg_command(
    ffmpeg_path: str,
    frame_pattern: Path,
    output_mp4: Path,
    fps: int,
    crf: int,
    preset: str,
    video_filter: str | None = None,
    audio_path: Path | None = None,
    audio_codec: str = "aac",
    audio_bitrate: str = "192k",
    audio_shortest: bool = True,
) -> list[str]:
    cmd = [
        ffmpeg_path,
        "-y",
        "-framerate",
        str(fps),
        "-i",
        str(frame_pattern),
    ]
    if audio_path is not None:
        cmd.extend(["-i", str(audio_path)])
    cmd.extend(
        [
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-crf",
            str(crf),
            "-preset",
            preset,
        ]
    )
    if video_filter:
        cmd.extend(["-vf", video_filter])
    if audio_path is not None:
        cmd.extend(["-c:a", audio_codec, "-b:a", audio_bitrate])
        if audio_shortest:
            cmd.append("-shortest")
    cmd.append(str(output_mp4))
    return cmd


def _seconds_to_srt_timestamp(seconds: float) -> str:
    total_ms = max(0, int(round(seconds * 1000)))
    h = total_ms // 3_600_000
    rem = total_ms % 3_600_000
    m = rem // 60_000
    rem = rem % 60_000
    s = rem // 1000
    ms = rem % 1000
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _build_subtitle_cues_from_manifest(manifest: dict) -> list[tuple[int, int, int, str]]:
    fps = int(manifest.get("fps", 30))
    if fps <= 0:
        raise ValueError("manifest fps must be > 0")
    slides = manifest.get("slides", [])
    frames = manifest.get("frames", [])
    if not isinstance(slides, list) or not isinstance(frames, list):
        raise ValueError("manifest slides/frames must be arrays")

    subtitle_by_index: dict[int, str] = {}
    for item in slides:
        if not isinstance(item, dict):
            continue
        idx = item.get("index")
        text = item.get("subtitle")
        if isinstance(idx, int) and isinstance(text, str):
            subtitle_by_index[idx] = text.strip()

    ranges: list[tuple[int, int, int, str]] = []
    active_idx: int | None = None
    start_frame: int | None = None
    for i, frame in enumerate(frames):
        if not isinstance(frame, dict):
            continue
        if frame.get("kind") == "hold":
            current_idx = frame.get("slideIndex")
        elif frame.get("kind") == "transition":
            current_idx = frame.get("toSlideIndex")
        else:
            current_idx = None
        if not isinstance(current_idx, int):
            continue
        if active_idx is None:
            active_idx = current_idx
            start_frame = i
            continue
        if current_idx != active_idx:
            text = subtitle_by_index.get(active_idx, "")
            if text and start_frame is not None:
                ranges.append((active_idx, start_frame, i, text))
            active_idx = current_idx
            start_frame = i
    if active_idx is not None and start_frame is not None:
        text = subtitle_by_index.get(active_idx, "")
        if text:
            ranges.append((active_idx, start_frame, len(frames), text))
    return ranges


def _write_srt_from_manifest(manifest: dict, srt_path: Path) -> Path:
    cues = _build_subtitle_cues_from_manifest(manifest)
    lines: list[str] = []
    fps = int(manifest.get("fps", 30))
    for idx, (_, start_f, end_f, text) in enumerate(cues, start=1):
        start_sec = start_f / fps
        end_sec = max(start_sec, end_f / fps)
        lines.extend(
            [
                str(idx),
                f"{_seconds_to_srt_timestamp(start_sec)} --> {_seconds_to_srt_timestamp(end_sec)}",
                text,
                "",
            ]
        )
    srt_path.write_text("\n".join(lines), encoding="utf-8")
    return srt_path


def _build_subtitle_filter(
    srt_path: Path,
    font_size: int,
    margin_v: int,
    alignment: int,
) -> str:
    safe_srt = str(srt_path.resolve()).replace("\\", "/")
    safe_srt = safe_srt.replace(":", "\\:").replace("'", "\\'")
    style = (
        "FontName=Arial,"
        f"FontSize={font_size},"
        "PrimaryColour=&H00FFFFFF,"
        "OutlineColour=&H00000000,"
        "BorderStyle=3,"
        "Outline=2,"
        "Shadow=0,"
        f"Alignment={alignment},"
        f"MarginV={margin_v}"
    )
    return f"subtitles=filename='{safe_srt}':force_style='{style}'"


def _escape_drawtext_text(text: str) -> str:
    escaped = text.replace("\\", "\\\\")
    escaped = escaped.replace(":", "\\:")
    escaped = escaped.replace("'", "\\'")
    escaped = escaped.replace(",", "\\,")
    escaped = escaped.replace("%", "\\%")
    return escaped


def _build_drawtext_filter_from_manifest(
    manifest: dict,
    font_size: int,
    margin_v: int,
    alignment: int,
) -> str:
    cues = _build_subtitle_cues_from_manifest(manifest)
    if alignment in {1, 4, 7}:
        x_expr = "20"
    elif alignment in {3, 6, 9}:
        x_expr = "w-text_w-20"
    else:
        x_expr = "(w-text_w)/2"
    if alignment in {7, 8, 9}:
        y_expr = "20"
    elif alignment in {4, 5, 6}:
        y_expr = "(h-text_h)/2"
    else:
        y_expr = f"h-text_h-{margin_v}"

    filters: list[str] = []
    fps = int(manifest.get("fps", 30))
    for _, start_f, end_f, text in cues:
        start_sec = start_f / fps
        end_sec = max(start_sec, end_f / fps)
        safe_text = _escape_drawtext_text(text)
        filters.append(
            "drawtext="
            "font='Arial':"
            f"text='{safe_text}':"
            f"fontsize={font_size}:"
            "fontcolor=white:"
            "borderw=2:"
            "bordercolor=black:"
            f"x={x_expr}:"
            f"y={y_expr}:"
            f"enable='between(t,{start_sec:.3f},{end_sec:.3f})'"
        )
    return ",".join(filters)


def _is_missing_filter_error(stderr: str, filter_name: str) -> bool:
    return f"No such filter: '{filter_name}'" in stderr or "Filter not found" in stderr


def render_video_from_frames(
    workspace: Path,
    output_mp4: Path | None = None,
    options: RenderVideoOptions | None = None,
) -> RenderVideoArtifacts:
    """
    Render MP4 from frame sequence generated by frame_capture.

    Expected workspace layout:
    - frame_manifest.json
    - frames/frame_000000.png ...
    """
    build = options or RenderVideoOptions()
    manifest_path = workspace / "frame_manifest.json"
    frame_dir = workspace / "frames"
    if not manifest_path.exists():
        raise FileNotFoundError(f"frame manifest not found: {manifest_path}")
    if not frame_dir.exists():
        raise FileNotFoundError(f"frame dir not found: {frame_dir}")

    manifest = _load_manifest(manifest_path)
    frame_count = int(manifest.get("totalFrames", 0))
    if frame_count <= 0:
        raise ValueError("manifest totalFrames must be > 0")

    fps = build.fps if build.fps is not None else int(manifest.get("fps", 30))
    if fps <= 0:
        raise ValueError("fps must be > 0")

    first_frame = frame_dir / "frame_000000.png"
    last_frame = frame_dir / f"frame_{frame_count - 1:06d}.png"
    if not first_frame.exists():
        raise FileNotFoundError(f"first frame missing: {first_frame}")
    if not last_frame.exists():
        raise FileNotFoundError(f"last frame missing: {last_frame}")

    out = output_mp4 or workspace / "deck.mp4"
    out.parent.mkdir(parents=True, exist_ok=True)
    frame_pattern = frame_dir / "frame_%06d.png"
    audio_path: Path | None = None
    if build.audio_path is not None:
        audio_path = build.audio_path
        if not audio_path.exists():
            raise FileNotFoundError(f"audio file not found: {audio_path}")

    subtitle_srt_path: Path | None = None
    video_filter: str | None = None
    if build.subtitle_mode == "burn":
        subtitle_srt_path = build.subtitle_srt_path or (workspace / "deck.subtitles.srt")
        if build.subtitle_srt_path is None:
            subtitle_srt_path = _write_srt_from_manifest(manifest, subtitle_srt_path)
        video_filter = _build_subtitle_filter(
            subtitle_srt_path,
            font_size=build.subtitle_font_size,
            margin_v=build.subtitle_margin_v,
            alignment=build.subtitle_alignment,
        )
    elif build.subtitle_mode != "none":
        raise ValueError("subtitle_mode must be `none` or `burn`")

    command = _build_ffmpeg_command(
        ffmpeg_path=build.ffmpeg_path,
        frame_pattern=frame_pattern,
        output_mp4=out,
        fps=fps,
        crf=build.crf,
        preset=build.preset,
        video_filter=video_filter,
        audio_path=audio_path,
        audio_codec=build.audio_codec,
        audio_bitrate=build.audio_bitrate,
        audio_shortest=build.audio_shortest,
    )
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    if completed.returncode != 0 and build.subtitle_mode == "burn" and video_filter is not None:
        if _is_missing_filter_error(completed.stderr, "subtitles"):
            video_filter = _build_drawtext_filter_from_manifest(
                manifest,
                font_size=build.subtitle_font_size,
                margin_v=build.subtitle_margin_v,
                alignment=build.subtitle_alignment,
            )
            command = _build_ffmpeg_command(
                ffmpeg_path=build.ffmpeg_path,
                frame_pattern=frame_pattern,
                output_mp4=out,
                fps=fps,
                crf=build.crf,
                preset=build.preset,
                video_filter=video_filter,
                audio_path=audio_path,
                audio_codec=build.audio_codec,
                audio_bitrate=build.audio_bitrate,
                audio_shortest=build.audio_shortest,
            )
            completed = subprocess.run(command, capture_output=True, text=True, check=False)
        if completed.returncode != 0 and _is_missing_filter_error(completed.stderr, "drawtext"):
            video_filter = None
            command = _build_ffmpeg_command(
                ffmpeg_path=build.ffmpeg_path,
                frame_pattern=frame_pattern,
                output_mp4=out,
                fps=fps,
                crf=build.crf,
                preset=build.preset,
                video_filter=None,
                audio_path=audio_path,
                audio_codec=build.audio_codec,
                audio_bitrate=build.audio_bitrate,
                audio_shortest=build.audio_shortest,
            )
            completed = subprocess.run(command, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        raise RuntimeError(
            "ffmpeg failed with exit code "
            f"{completed.returncode}: {completed.stderr.strip()}"
        )
    if not out.exists() or out.stat().st_size <= 0:
        raise RuntimeError(f"render output missing or empty: {out}")

    return RenderVideoArtifacts(
        output_mp4=out,
        frame_count=frame_count,
        fps=fps,
        command=command,
        subtitle_srt_path=subtitle_srt_path,
        audio_path=audio_path,
    )
