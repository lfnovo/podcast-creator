# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Configurable silence between dialogue turns in the combined audio: `audio_gap_ms` on episode profiles and `create_podcast()` (default 400 ms, `0` disables) (#37)

### Fixed
- Streamlit UI URL and file extraction works with content-core 2.x, whose `extract_content()` takes keyword arguments
- Combining audio no longer truncates speech when TTS-generated MP3 clips declare an inaccurate duration in their headers; clips are now decoded to their real end (#41, #42)
- Combining audio now uses a single ffmpeg process regardless of the number of clips, fixing `[Errno 11] Resource temporarily unavailable` on long episodes in hosts with process limits (#42)
- `combine_audio_files` raises `ValueError` / `RuntimeError` on failure instead of returning an `"ERROR: ..."` string, so `create_podcast()` no longer reports a failed episode as a file path (#44)

### Changed
- Outline and transcript generation request schema-driven structured output (`json_schema` with the `Outline` / validated transcript schemas) instead of generic JSON, so providers return the expected shape and Anthropic no longer warns about prompt-guided JSON (#38). Models without JSON-schema support can fall back with `outline_config` / `transcript_config` = `{"structured": {"type": "json"}}`
- Minimum dependency versions raised to `esperanto>=2.28.0` and `content-core>=2.2.0`
- Default transcript model changed from `claude-3-5-sonnet-latest` to `claude-sonnet-5-5` in `create_podcast()`, `EpisodeProfile` and all bundled episode profiles: Anthropic has retired the Claude 3 family, so the previous default failed on every request
- Streamlit UI default models updated for retired ones (Anthropic → `claude-sonnet-5-5`, Gemini → `gemini-2.5-flash` / `gemini-2.5-pro`, Groq → `openai/gpt-oss-120b`)
- Audio combining uses ffmpeg's concat filter (via the ffmpeg binary bundled with `imageio-ffmpeg`) instead of MoviePy; clips with different sample rates or channel layouts are normalized to the first clip's format
- `moviepy` is no longer a direct dependency; `imageio-ffmpeg` is
- Default `max_tokens` raised from 3000 to 8192 for outline generation and from 5000 to 8192 for transcript generation, avoiding truncated outlines and malformed transcript JSON with dense content (#34). Override via `outline_config` / `transcript_config`
- The combined episode now has a 400 ms pause between turns by default; pass `audio_gap_ms=0` for the previous back-to-back output
- **Breaking for callers of `combine_audio_files`:** code that checked `combined_audio_path` for an `"ERROR:"` prefix must catch exceptions instead

## [0.12.0] - 2026-02-18

### Added
- `language` parameter for multilingual podcast generation — accepts ISO 639-1 (`pt`) or BCP 47 (`pt-BR`) codes to instruct LLMs to generate outlines and transcripts in the specified language
- New `resolve_language_name()` utility for resolving language codes to full names via `pycountry`
- `language` field on `EpisodeProfile` for per-profile language defaults

## [0.11.2] - 2026-02-17

### Fixed
- Retry now covers both LLM call and JSON parsing — previously only the `ainvoke()` call was retried, so invalid JSON responses from the LLM were not retried

## [0.11.1] - 2026-02-17

### Fixed
- HTTP 4xx client errors (e.g. 404 model not found, 401 auth failure) are no longer retried — only transient errors and 429 rate-limit are retried
- Increased default retry backoff multiplier from 2s to 5s for more reasonable wait times

## [0.11.0] - 2026-02-17

### Added
- Automatic retry with exponential backoff for transient failures in LLM and TTS API calls using tenacity
- New `retry.py` module with configurable retry logic (max attempts, backoff multiplier, max wait)
- Non-retryable exceptions (ValueError, TypeError, etc.) are raised immediately without retry
- Environment variable configuration: `PODCAST_RETRY_MAX_ATTEMPTS`, `PODCAST_RETRY_WAIT_MULTIPLIER`, `PODCAST_RETRY_WAIT_MAX`
- Programmatic retry configuration via `retry_max_attempts` and `retry_wait_multiplier` parameters in `create_podcast()`

## [0.10.0] - 2026-02-17

### Added
- Per-speaker TTS provider, model, and config overrides — individual speakers can now use different TTS services within the same podcast (e.g., one speaker on ElevenLabs and another on OpenAI TTS)

## [0.9.4] - 2026-02-17

### Fixed
- Default `Segment.size` to "medium" when LLM omits the field, preventing Pydantic validation errors during outline generation (e.g. with Gemini models)

## [0.9.3] - 2026-02-17

### Fixed
- Handle unclosed `<think>` tags from models (e.g. DeepSeek) that omit the closing `</think>` tag, which caused JSON parsing failures in transcript and outline generation

## [0.9.2] - 2026-02-16

### Fixed
- Fix `configure()` call in Streamlit UI using incorrect keyword argument syntax
- Update Streamlit optional dependency version constraint

## [0.9.1] - 2026-02-16

### Fixed
- Handle structured content format from LLM providers (Google Gemini, DeepSeek) that return `AIMessage.content` as a list instead of a string (#19)

## [0.9.0] - 2026-01-29

### Changed
- **BREAKING**: Simplified proxy configuration to use standard environment variables only
- Removed custom `proxy` parameter from `create_podcast()` function
- Removed `PODCAST_CREATOR_PROXY` environment variable support
- Removed `get_proxy()` utility function
- Proxy support now relies entirely on standard `HTTP_PROXY`, `HTTPS_PROXY`, and `NO_PROXY` environment variables
- Underlying libraries (esperanto, content-core) handle proxy configuration automatically

### Removed
- `podcast_creator.utils` module (proxy utilities)

## [0.8.0] - 2026-01-26

### Added
- HTTP/HTTPS proxy support for all network requests
- New `proxy` parameter in `create_podcast()` function for runtime proxy configuration
- Environment variable support: `PODCAST_CREATOR_PROXY` with fallback to `HTTP_PROXY`/`HTTPS_PROXY`
- Proxy configuration propagates to all AI provider calls (LLM, TTS) via esperanto
- Proxy configuration propagates to content extraction via content-core
- New `get_proxy()` utility function in `podcast_creator.utils`
- Proxy logging with credential redaction for security
- Unit tests for proxy resolution logic
- Documentation for proxy configuration in README

### Fixed
- Fixed duplicate return statement in `combine_audio_node`
- Added missing type annotation for `transcript` variable in nodes.py

## [0.7.3] - 2025-01-15

### Fixed
- Remove duplicate resources inclusion in wheel build (#13)

## [0.7.2] - 2025-01-14

### Changed
- Dependency updates

## [0.7.1] - 2025-01-13

### Fixed
- Pass transcript through to prompts to create better scripts

## [0.7.0] - 2025-01-10

### Added
- Make TTS batch size configurable via `TTS_BATCH_SIZE` environment variable
- Comprehensive contribution documentation (#11)
- Interactive file overwrite confirmation in CLI init command (#4)

## [0.5.0] - 2025-01-05

### Fixed
- Content input parameter now accepts string or array of strings

## [0.4.1] - 2025-01-03

### Changed
- Reduced request dependency requirements

## [0.4.0] - 2025-01-02

### Added
- Make Streamlit an optional dependency for better library experience
- Core library can now be used without installing Streamlit UI dependencies

## [0.3.1] - 2024-12-28

### Fixed
- Make segments less apparent in output
- Documentation improvements

## [0.3.0] - 2024-12-25

### Added
- Initial public release
- LangGraph-based podcast generation workflow
- Support for multiple AI providers via esperanto
- Streamlit web interface
- CLI with init command
- Episode profiles for quick configuration
- Speaker configuration system
