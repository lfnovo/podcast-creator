# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build and Development Commands

```bash
# Install dependencies using uv (preferred)
uv sync

# Run tests
uv run pytest -v
# or
make test

# Run linting/type checking
uv run python -m mypy .
# or
make lint

# Run code formatting with ruff
ruff check . --fix
# or
make ruff

# Run a single test
uv run pytest tests/test_cli.py::test_specific_function -v

# Create a version tag
make tag

# Install for development (editable mode)
uv pip install -e .

# Launch web interface (requires UI installation)
uv run podcast-creator ui

# Initialize templates and configs
uv run podcast-creator init
```

## High-Level Architecture

This is a **LangGraph-based podcast generation system** that transforms text content into conversational audio podcasts through an AI-powered workflow pipeline.

### Core Workflow Pipeline

The system follows a state machine workflow implemented with LangGraph:

```
START → generate_outline → generate_transcript → generate_all_audio → combine_audio → END
```

Each node in the workflow:
- **generate_outline**: Uses AI to structure content into podcast segments
- **generate_transcript**: Creates natural dialogue between speakers
- **generate_all_audio**: Converts text to speech in batches (5 clips at a time)
- **combine_audio**: Merges individual clips into final podcast

### Key Architectural Components

1. **State Management** (`state.py`): 
   - Uses `PodcastState` TypedDict to track workflow progress
   - Manages content transformation from input → outline → transcript → audio

2. **Configuration System** (`config.py`):
   - Singleton `ConfigurationManager` with priority cascade:
     - User inline config → File paths → Working directory → Package defaults
   - Supports templates, speakers, and episode profiles

3. **Multi-Provider Abstraction**:
   - Uses `esperanto` library for unified AI provider access
   - Supports OpenAI, Anthropic, Google, ElevenLabs, etc.
   - Provider-agnostic implementation allows easy switching

4. **Template-Driven Prompting**:
   - Uses `ai-prompter` with Jinja2 templates
   - Templates in `prompts/podcast/` directory
   - Separates prompt engineering from code logic

5. **Episode Profiles** (`episodes.py`):
   - Pre-configured podcast settings for common use cases
   - Reduces configuration from ~12 parameters to ~4
   - Profiles: `tech_discussion`, `solo_expert`, `business_analysis`, `diverse_panel`

6. **Retry / Resilience** (`retry.py`):
   - Tenacity-based retry with exponential backoff for transient API failures
   - Non-retryable exceptions (ValueError, TypeError, etc.) bypass retry
   - Configurable via `configurable` dict, env vars, or hardcoded defaults

### Important Design Patterns

- **Async-First**: All AI operations are async for performance
- **Batch Processing**: Audio generation respects API rate limits (5 clips/batch)
- **Retry with Backoff**: LLM and TTS calls retry on transient errors (configurable via env vars or `create_podcast()` params)
- **Validated Outputs**: Uses Pydantic models with runtime validation
- **Resource Fallbacks**: Multiple paths for loading templates/configs
- **Clean Dialogue**: Filters AI thinking tags (`<think>`) from TTS input

### Entry Points

1. **Library API**: `create_podcast()` in `graph.py`
2. **CLI**: Commands in `cli.py` (init, ui, version)
3. **Web UI**: Streamlit app in `resources/streamlit_app/`

### Key Dependencies

- **LangGraph**: Workflow orchestration
- **esperanto**: Multi-provider AI abstraction
- **ai-prompter**: Template management
- **content-core**: Content extraction from files/URLs
- **tenacity**: Retry with exponential backoff
- **pydub/moviepy**: Audio processing

This architecture enables flexible, scalable podcast generation while maintaining clean separation of concerns through configuration-driven design.