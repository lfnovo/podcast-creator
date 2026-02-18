# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
