"""
Tests for combine_audio_files using real audio generated with ffmpeg
"""

import array
import asyncio
import re
import subprocess
import sys
from pathlib import Path

import pytest
from imageio_ffmpeg import get_ffmpeg_exe  # type: ignore[import-untyped]

from podcast_creator.core import combine_audio_files
from podcast_creator.nodes import combine_audio_node

FFMPEG = get_ffmpeg_exe()


def make_tone(
    path: Path,
    seconds: float,
    rate: int = 22050,
    layout: str = "mono",
    frequency: int = 440,
):
    """Write a CBR MP3 sine tone with an accurate duration."""
    subprocess.run(
        [
            FFMPEG, "-hide_banner", "-loglevel", "error", "-y",
            "-f", "lavfi", "-i", f"sine=frequency={frequency}:sample_rate={rate}:duration={seconds}",
            "-af", f"aformat=channel_layouts={layout}",
            "-c:a", "libmp3lame", "-b:a", "64k", str(path),
        ],
        check=True,
    )


def make_misleading_header_clip(path: Path):
    """Write a ~5s VBR MP3 without a Xing header whose estimated duration is ~2.7s.

    A loud first second followed by silence makes the bitrate-based estimate much
    shorter than the decoded audio, the same failure mode as TTS clips in #41.
    """
    subprocess.run(
        [
            FFMPEG, "-hide_banner", "-loglevel", "error", "-y",
            "-f", "lavfi", "-i", "anoisesrc=r=22050:d=1:a=0.5",
            "-f", "lavfi", "-i", "anullsrc=r=22050:cl=mono:d=4",
            "-filter_complex", "[0:a]aformat=channel_layouts=mono[n];[n][1:a]concat=n=2:v=0:a=1",
            "-c:a", "libmp3lame", "-q:a", "9", "-write_xing", "0", str(path),
        ],
        check=True,
    )


def header_duration(path: Path) -> float:
    """Duration as declared/estimated from the container, without decoding."""
    stderr = subprocess.run(
        [FFMPEG, "-hide_banner", "-i", str(path)], capture_output=True, text=True
    ).stderr
    match = re.search(r"Duration: (\d+):(\d+):([\d.]+)", stderr)
    assert match, stderr
    h, m, s = match.groups()
    return int(h) * 3600 + int(m) * 60 + float(s)


def decoded_duration(path: Path) -> float:
    """Duration obtained by decoding the whole file."""
    stdout = subprocess.run(
        [FFMPEG, "-hide_banner", "-nostats", "-i", str(path), "-f", "null", "-progress", "pipe:1", "-"],
        capture_output=True, text=True, check=True,
    ).stdout
    return int(re.findall(r"out_time_us=(\d+)", stdout)[-1]) / 1_000_000


def dominant_frequencies(path: Path, window_starts, window: float = 0.4, rate: int = 8000):
    """Estimate the tone frequency in each window from zero crossings of the decoded audio."""
    raw = subprocess.run(
        [FFMPEG, "-hide_banner", "-loglevel", "error", "-i", str(path),
         "-f", "s16le", "-ac", "1", "-ar", str(rate), "-"],
        capture_output=True, check=True,
    ).stdout
    samples = array.array("h", raw)
    frequencies = []
    for start in window_starts:
        chunk = samples[int(start * rate): int((start + window) * rate)]
        crossings = sum(1 for a, b in zip(chunk, chunk[1:]) if (a < 0) != (b < 0))
        frequencies.append(crossings / 2 / window)
    return frequencies


def stream_info(path: Path) -> str:
    stderr = subprocess.run(
        [FFMPEG, "-hide_banner", "-i", str(path)], capture_output=True, text=True
    ).stderr
    match = re.search(r"Audio: .*", stderr)
    assert match, stderr
    return match.group(0)


class TestCombineAudioFiles:
    def test_combines_clips_in_order_with_full_duration(self, tmp_path):
        clips = tmp_path / "clips"
        clips.mkdir()
        for i, seconds in enumerate([1.0, 2.0, 1.5]):
            make_tone(clips / f"{i:04d}.mp3", seconds)

        result = asyncio.run(combine_audio_files(clips, "episode", tmp_path / "audio"))

        output = Path(result["combined_audio_path"])
        assert output == (tmp_path / "audio" / "episode.mp3").resolve()
        assert result["original_segments_count"] == 3
        assert decoded_duration(output) == pytest.approx(4.5, abs=0.15)
        assert result["total_duration_seconds"] == pytest.approx(4.5, abs=0.15)
        assert "22050 Hz, mono" in stream_info(output)

    def test_keeps_clip_order(self, tmp_path):
        clips = tmp_path / "clips"
        clips.mkdir()
        # Written out of order on purpose; the file name decides the order
        for name, frequency in [("0002", 1500), ("0000", 300), ("0001", 800)]:
            make_tone(clips / f"{name}.mp3", 1.0, frequency=frequency)

        result = asyncio.run(combine_audio_files(clips, "episode", tmp_path / "audio"))

        first, second, third = dominant_frequencies(
            Path(result["combined_audio_path"]), [0.3, 1.3, 2.3]
        )
        assert first == pytest.approx(300, rel=0.1)
        assert second == pytest.approx(800, rel=0.1)
        assert third == pytest.approx(1500, rel=0.1)

    def test_preserves_audio_when_mp3_header_duration_is_wrong(self, tmp_path):
        """Regression for #41: clips must not be cut at their declared duration."""
        clips = tmp_path / "clips"
        clips.mkdir()
        for i in range(2):
            make_misleading_header_clip(clips / f"{i:04d}.mp3")

        first = clips / "0000.mp3"
        real = decoded_duration(first)
        assert header_duration(first) < real - 1.5, "fixture must have a misleading header"

        result = asyncio.run(combine_audio_files(clips, "episode.mp3", tmp_path / "audio"))

        assert decoded_duration(Path(result["combined_audio_path"])) == pytest.approx(
            2 * real, abs=0.2
        )

    def test_uses_bounded_processes_regardless_of_clip_count(self, tmp_path, monkeypatch):
        """Regression for #42: one ffmpeg process per clip exhausted pid limits."""
        clips = tmp_path / "clips"
        clips.mkdir()
        for i in range(30):
            make_tone(clips / f"{i:04d}.mp3", 0.2)

        calls = []
        original = asyncio.create_subprocess_exec

        async def counting_exec(*args, **kwargs):
            calls.append(args)
            return await original(*args, **kwargs)

        monkeypatch.setattr(asyncio, "create_subprocess_exec", counting_exec)

        result = asyncio.run(combine_audio_files(clips, "episode", tmp_path / "audio"))

        assert len(calls) == 2  # one format probe + one combine
        assert result["original_segments_count"] == 30
        assert decoded_duration(Path(result["combined_audio_path"])) == pytest.approx(
            6.0, abs=0.3
        )

    def test_normalizes_clips_with_different_formats(self, tmp_path):
        clips = tmp_path / "clips"
        clips.mkdir()
        make_tone(clips / "0000.mp3", 1.0, rate=22050, layout="mono")
        make_tone(clips / "0001.mp3", 1.0, rate=44100, layout="stereo")

        result = asyncio.run(combine_audio_files(clips, "episode", tmp_path / "audio"))

        output = Path(result["combined_audio_path"])
        assert decoded_duration(output) == pytest.approx(2.0, abs=0.15)
        assert "22050 Hz, mono" in stream_info(output)

    def test_raises_when_no_clips(self, tmp_path):
        clips = tmp_path / "clips"
        clips.mkdir()

        with pytest.raises(ValueError, match="no .mp3 clips"):
            asyncio.run(combine_audio_files(clips, "episode", tmp_path / "audio"))

    def test_raises_and_cleans_up_when_ffmpeg_fails(self, tmp_path):
        clips = tmp_path / "clips"
        clips.mkdir()
        make_tone(clips / "0000.mp3", 0.5)
        (clips / "0001.mp3").write_bytes(b"not an mp3 file")

        with pytest.raises(RuntimeError, match="ffmpeg exited with code"):
            asyncio.run(combine_audio_files(clips, "episode", tmp_path / "audio"))

        assert list((tmp_path / "audio").iterdir()) == []


    def test_raises_runtime_error_when_ffmpeg_cannot_start(self, tmp_path, monkeypatch):
        clips = tmp_path / "clips"
        clips.mkdir()
        make_tone(clips / "0000.mp3", 0.5)
        monkeypatch.setattr(
            "podcast_creator.core.get_ffmpeg_exe", lambda: str(tmp_path / "missing-ffmpeg")
        )

        with pytest.raises(RuntimeError, match="failed to run ffmpeg"):
            asyncio.run(combine_audio_files(clips, "episode", tmp_path / "audio"))

        assert not (tmp_path / "audio" / "episode.mp3").exists()

    def test_cancellation_kills_ffmpeg_and_removes_partial_output(self, tmp_path, monkeypatch):
        clips = tmp_path / "clips"
        clips.mkdir()
        make_tone(clips / "0000.mp3", 0.5)
        processes = []
        original = asyncio.create_subprocess_exec

        async def slow_ffmpeg(*args, **kwargs):
            if "-filter_complex" not in args:
                return await original(*args, **kwargs)
            # Stand-in for a long combine: write partial output, then hang
            Path(args[-1]).write_bytes(b"partial")
            process = await original(
                sys.executable, "-c", "import time; time.sleep(30)", **kwargs
            )
            processes.append(process)
            return process

        monkeypatch.setattr(asyncio, "create_subprocess_exec", slow_ffmpeg)

        async def run_and_cancel():
            task = asyncio.create_task(
                combine_audio_files(clips, "episode", tmp_path / "audio")
            )
            while not processes:
                await asyncio.sleep(0.01)
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task

        asyncio.run(run_and_cancel())

        assert processes[0].returncode is not None
        assert list((tmp_path / "audio").iterdir()) == []

    def test_failure_keeps_existing_episode(self, tmp_path):
        clips = tmp_path / "clips"
        clips.mkdir()
        make_tone(clips / "0000.mp3", 0.5)
        (clips / "0001.mp3").write_bytes(b"not an mp3 file")
        existing = tmp_path / "audio" / "episode.mp3"
        existing.parent.mkdir()
        existing.write_bytes(b"previous episode")

        with pytest.raises(RuntimeError):
            asyncio.run(combine_audio_files(clips, "episode", tmp_path / "audio"))

        assert existing.read_bytes() == b"previous episode"
        assert list(existing.parent.iterdir()) == [existing]


class TestCombineAudioNode:
    def test_propagates_failure_instead_of_returning_error_path(self, tmp_path):
        """Regression for #44: failures used to come back as Path("ERROR: ...")."""
        (tmp_path / "clips").mkdir()
        state = {"output_dir": tmp_path, "episode_name": "episode"}

        with pytest.raises(ValueError):
            asyncio.run(combine_audio_node(state, {}))

    def test_returns_combined_file_path(self, tmp_path):
        (tmp_path / "clips").mkdir()
        make_tone(tmp_path / "clips" / "0000.mp3", 0.5)
        state = {"output_dir": tmp_path, "episode_name": "episode"}

        result = asyncio.run(combine_audio_node(state, {}))

        assert result["final_output_file_path"] == (tmp_path / "audio" / "episode.mp3").resolve()
        assert result["final_output_file_path"].exists()
