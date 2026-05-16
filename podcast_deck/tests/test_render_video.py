from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from click.testing import CliRunner

import podcast_deck.cli as cli_module
from podcast_deck.frame_capture import FrameCaptureArtifacts
from podcast_deck.render_video import (
    _build_ffmpeg_command,
    _build_subtitle_cues_from_manifest,
    _build_subtitle_filter,
    _build_drawtext_filter_from_manifest,
    _seconds_to_srt_timestamp,
    _write_srt_from_manifest,
    RenderVideoOptions,
    RenderVideoArtifacts,
    render_video_from_frames,
)


def _prepare_workspace(tmp_path: Path, total_frames: int = 2) -> Path:
    workspace = tmp_path / "video-workspace"
    frame_dir = workspace / "frames"
    frame_dir.mkdir(parents=True, exist_ok=True)
    for i in range(total_frames):
        (frame_dir / f"frame_{i:06d}.png").write_bytes(b"fake-png")
    manifest = {
        "fps": 10,
        "width": 640,
        "height": 360,
        "slides": [
            {"index": 0, "id": "s1", "subtitle": "第一页 / 要点A"},
            {"index": 1, "id": "s2", "subtitle": "第二页 / 要点B"},
        ],
        "holdFramesPerSlide": 1,
        "transitionFramesPerGap": 0,
        "totalFrames": total_frames,
        "frames": [
            {"index": i, "kind": "hold", "path": f"frame_{i:06d}.png"}
            for i in range(total_frames)
        ],
    }
    (workspace / "frame_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False), encoding="utf-8"
    )
    return workspace


def test_build_ffmpeg_command_contains_expected_flags(tmp_path: Path) -> None:
    cmd = _build_ffmpeg_command(
        ffmpeg_path="ffmpeg",
        frame_pattern=tmp_path / "frames" / "frame_%06d.png",
        output_mp4=tmp_path / "deck.mp4",
        fps=10,
        crf=18,
        preset="medium",
    )
    assert cmd[:4] == ["ffmpeg", "-y", "-framerate", "10"]
    assert "-c:v" in cmd
    assert "libx264" in cmd
    assert "-pix_fmt" in cmd
    assert "yuv420p" in cmd


def test_build_ffmpeg_command_includes_audio_mux_flags(tmp_path: Path) -> None:
    audio = tmp_path / "narration.mp3"
    audio.write_bytes(b"fake-audio")
    cmd = _build_ffmpeg_command(
        ffmpeg_path="ffmpeg",
        frame_pattern=tmp_path / "frames" / "frame_%06d.png",
        output_mp4=tmp_path / "deck.mp4",
        fps=10,
        crf=18,
        preset="medium",
        audio_path=audio,
        audio_codec="aac",
        audio_bitrate="128k",
        audio_shortest=True,
    )
    assert str(audio) in cmd
    assert "-c:a" in cmd
    assert "aac" in cmd
    assert "-b:a" in cmd
    assert "128k" in cmd
    assert "-shortest" in cmd


def test_build_ffmpeg_command_can_include_video_filter(tmp_path: Path) -> None:
    cmd = _build_ffmpeg_command(
        ffmpeg_path="ffmpeg",
        frame_pattern=tmp_path / "frames" / "frame_%06d.png",
        output_mp4=tmp_path / "deck.mp4",
        fps=10,
        crf=18,
        preset="medium",
        video_filter="subtitles='deck.srt'",
    )
    assert "-vf" in cmd
    assert "subtitles='deck.srt'" in cmd


def test_seconds_to_srt_timestamp() -> None:
    assert _seconds_to_srt_timestamp(0.0) == "00:00:00,000"
    assert _seconds_to_srt_timestamp(61.25) == "00:01:01,250"


def test_build_subtitle_cues_from_manifest() -> None:
    manifest = {
        "fps": 10,
        "slides": [
            {"index": 0, "subtitle": "A"},
            {"index": 1, "subtitle": "B"},
        ],
        "frames": [
            {"kind": "hold", "slideIndex": 0, "path": "frame_000000.png"},
            {"kind": "hold", "slideIndex": 0, "path": "frame_000001.png"},
            {"kind": "transition", "toSlideIndex": 1, "path": "frame_000002.png"},
            {"kind": "hold", "slideIndex": 1, "path": "frame_000003.png"},
        ],
    }
    cues = _build_subtitle_cues_from_manifest(manifest)
    assert len(cues) == 2
    assert cues[0][0] == 0
    assert cues[0][3] == "A"
    assert cues[1][0] == 1
    assert cues[1][3] == "B"


def test_write_srt_from_manifest(tmp_path: Path) -> None:
    manifest = {
        "fps": 10,
        "slides": [{"index": 0, "subtitle": "字幕A"}],
        "frames": [
            {"kind": "hold", "slideIndex": 0, "path": "frame_000000.png"},
            {"kind": "hold", "slideIndex": 0, "path": "frame_000001.png"},
        ],
    }
    out = _write_srt_from_manifest(manifest, tmp_path / "deck.srt")
    content = out.read_text(encoding="utf-8")
    assert "00:00:00,000 --> 00:00:00,200" in content
    assert "字幕A" in content


def test_build_subtitle_filter_escapes_path(tmp_path: Path) -> None:
    path = tmp_path / "my subtitle's file.srt"
    path.write_text("1\n00:00:00,000 --> 00:00:01,000\nx\n", encoding="utf-8")
    vf = _build_subtitle_filter(path, font_size=28, margin_v=36, alignment=2)
    assert "subtitles=filename='" in vf
    assert "force_style='" in vf


def test_build_drawtext_filter_from_manifest() -> None:
    manifest = {
        "fps": 10,
        "slides": [{"index": 0, "subtitle": "字幕A"}],
        "frames": [
            {"kind": "hold", "slideIndex": 0, "path": "frame_000000.png"},
            {"kind": "hold", "slideIndex": 0, "path": "frame_000001.png"},
        ],
    }
    vf = _build_drawtext_filter_from_manifest(
        manifest, font_size=24, margin_v=30, alignment=2
    )
    assert "drawtext=" in vf
    assert "between(t," in vf
    assert "字幕A" in vf


def test_render_video_from_frames_raises_when_manifest_missing(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        render_video_from_frames(tmp_path)


def test_render_video_from_frames_raises_on_ffmpeg_failure(tmp_path: Path) -> None:
    workspace = _prepare_workspace(tmp_path, total_frames=2)
    with pytest.raises(RuntimeError):
        render_video_from_frames(
            workspace=workspace,
            output_mp4=workspace / "deck.mp4",
        )


def test_render_video_from_frames_raises_when_audio_missing(tmp_path: Path) -> None:
    workspace = _prepare_workspace(tmp_path, total_frames=2)
    with pytest.raises(FileNotFoundError):
        render_video_from_frames(
            workspace=workspace,
            output_mp4=workspace / "deck.mp4",
            options=RenderVideoOptions(audio_path=workspace / "missing.mp3"),
        )


def test_render_video_from_frames_generates_srt_in_burn_mode(tmp_path: Path) -> None:
    workspace = _prepare_workspace(tmp_path, total_frames=2)
    with pytest.raises(RuntimeError):
        render_video_from_frames(
            workspace=workspace,
            output_mp4=workspace / "deck.mp4",
            options=RenderVideoOptions(subtitle_mode="burn"),
        )
    assert (workspace / "deck.subtitles.srt").exists()


def test_render_video_from_frames_falls_back_when_subtitle_filters_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workspace = _prepare_workspace(tmp_path, total_frames=2)
    calls: list[list[str]] = []

    def _fake_run(command, capture_output, text, check):  # noqa: ANN001
        calls.append(command)
        if len(calls) == 1:
            return SimpleNamespace(returncode=1, stderr="No such filter: 'subtitles'")
        if len(calls) == 2:
            return SimpleNamespace(returncode=1, stderr="No such filter: 'drawtext'")
        Path(command[-1]).write_bytes(b"mp4")
        return SimpleNamespace(returncode=0, stderr="")

    monkeypatch.setattr("podcast_deck.render_video.subprocess.run", _fake_run)
    monkeypatch.setattr(
        "podcast_deck.render_video._build_drawtext_filter_from_manifest",
        lambda manifest, font_size, margin_v, alignment: "drawtext=text='x'",
    )
    artifacts = render_video_from_frames(
        workspace=workspace,
        output_mp4=workspace / "deck.mp4",
        options=RenderVideoOptions(subtitle_mode="burn"),
    )
    assert artifacts.output_mp4.exists()
    assert len(calls) == 3
    assert "-vf" in calls[0]
    assert any("subtitles=filename=" in part for part in calls[0])
    assert "-vf" in calls[1]
    assert any("drawtext=" in part for part in calls[1])
    assert "-vf" not in calls[2]


def test_synth_video_cmd_runs_capture_then_render(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    input_json = tmp_path / "deck.json"
    input_json.write_text(
        json.dumps(
            {
                "schemaVersion": "1.0",
                "meta": {"title": "x", "lang": "zh-CN"},
                "slides": [{"id": "s1", "content": "a"}],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    workspace = tmp_path / "workspace"
    workspace.mkdir(parents=True, exist_ok=True)

    called: dict[str, object] = {}

    def _fake_capture(input_json_path, workspace, options):
        called["capture_input"] = input_json_path
        called["capture_workspace"] = workspace
        called["capture_fps"] = options.fps
        manifest = workspace / "frame_manifest.json"
        manifest.write_text("{}", encoding="utf-8")
        return FrameCaptureArtifacts(
            frame_dir=workspace / "frames",
            slides_dir=workspace / "slides",
            manifest_path=manifest,
            total_frames=3,
            fps=options.fps,
            hold_frames_per_slide=1,
            transition_frames_per_gap=0,
        )

    def _fake_render(workspace, output_mp4, options):
        called["render_workspace"] = workspace
        called["render_output_mp4"] = output_mp4
        called["render_subtitle_mode"] = options.subtitle_mode
        return RenderVideoArtifacts(
            output_mp4=output_mp4 or (workspace / "deck.mp4"),
            frame_count=3,
            fps=options.fps or 30,
            command=["ffmpeg"],
            subtitle_srt_path=None,
            audio_path=options.audio_path,
        )

    monkeypatch.setattr(cli_module, "capture_frame_sequence", _fake_capture)
    monkeypatch.setattr(cli_module, "render_video_from_frames", _fake_render)

    runner = CliRunner()
    result = runner.invoke(
        cli_module.cli,
        [
            "synth-video",
            "--input",
            str(input_json),
            "--workspace",
            str(workspace),
            "--fps",
            "12",
            "--subtitle-mode",
            "burn",
        ],
    )
    assert result.exit_code == 0, result.output
    assert called["capture_input"] == input_json
    assert called["capture_workspace"] == workspace
    assert called["capture_fps"] == 12
    assert called["render_workspace"] == workspace
    assert called["render_subtitle_mode"] == "burn"


def test_synth_video_cmd_can_clean_workspace(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    input_json = tmp_path / "deck.json"
    input_json.write_text(
        json.dumps(
            {
                "schemaVersion": "1.0",
                "meta": {"title": "x", "lang": "zh-CN"},
                "slides": [{"id": "s1", "content": "a"}],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    workspace = tmp_path / "workspace-clean"
    workspace.mkdir(parents=True, exist_ok=True)
    output_mp4 = workspace / "deck.final.mp4"

    def _fake_capture(input_json_path, workspace, options):
        (workspace / "frames").mkdir(parents=True, exist_ok=True)
        (workspace / "slides").mkdir(parents=True, exist_ok=True)
        manifest = workspace / "frame_manifest.json"
        manifest.write_text("{}", encoding="utf-8")
        return FrameCaptureArtifacts(
            frame_dir=workspace / "frames",
            slides_dir=workspace / "slides",
            manifest_path=manifest,
            total_frames=3,
            fps=options.fps,
            hold_frames_per_slide=1,
            transition_frames_per_gap=0,
        )

    def _fake_render(workspace, output_mp4, options):
        assert output_mp4 is not None
        output_mp4.write_bytes(b"mp4")
        subtitle = workspace / "deck.subtitles.srt"
        subtitle.write_text("1\n00:00:00,000 --> 00:00:01,000\nx\n", encoding="utf-8")
        return RenderVideoArtifacts(
            output_mp4=output_mp4,
            frame_count=3,
            fps=options.fps or 30,
            command=["ffmpeg"],
            subtitle_srt_path=subtitle,
            audio_path=options.audio_path,
        )

    monkeypatch.setattr(cli_module, "capture_frame_sequence", _fake_capture)
    monkeypatch.setattr(cli_module, "render_video_from_frames", _fake_render)

    runner = CliRunner()
    result = runner.invoke(
        cli_module.cli,
        [
            "synth-video",
            "--input",
            str(input_json),
            "--workspace",
            str(workspace),
            "--output-mp4",
            str(output_mp4),
            "--subtitle-mode",
            "burn",
            "--clean-workspace",
        ],
    )
    assert result.exit_code == 0, result.output
    assert output_mp4.exists()
    assert not (workspace / "frames").exists()
    assert not (workspace / "slides").exists()
    assert not (workspace / "frame_manifest.json").exists()
    assert not (workspace / "deck.subtitles.srt").exists()
