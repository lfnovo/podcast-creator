# Gotchas

Fragile areas and lessons learned. The release retro appends here; a gotcha that holds up
three times graduates to the process document or to a test.

- `combine_audio_files` (`core.py`) uses moviepy, which opens one ffmpeg subprocess per clip
  and trusts MP3 header durations. Long episodes can hit process limits (#42) and clips with
  inaccurate duration metadata get truncated (#41).
- `.github/workflows/create-tag.yml` pushes the tag with `GITHUB_TOKEN`; tags pushed that way
  do not trigger other workflows, so `publish.yml` likely does not run from it. `make tag`
  (pushed with the maintainer's credentials) is the path that publishes. Unverified.
