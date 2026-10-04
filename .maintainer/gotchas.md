# Gotchas

Fragile areas and lessons learned. The release retro appends here; a gotcha that holds up
three times graduates to the process document or to a test.

- `combine_audio_files` (`core.py`) must stay a single ffmpeg filter-concat with per-input
  `asetpts=PTS-STARTPTS`: MoviePy opened one process per clip (#42) and the concat demuxer with
  `-c copy` truncates TTS clips with wrong MP3 header durations (#41).
- Tags pushed with `GITHUB_TOKEN` do not trigger other workflows. `create-tag.yml` therefore
  calls `publish.yml` directly (`workflow_call`) after creating the tag; `make tag` (pushed
  with the maintainer's credentials) triggers `publish.yml` through the tag push.
