# Podcast Creator

An AI-powered podcast generation library that creates conversational audio content from text-based sources. This pip-installable package processes documents, generates structured outlines, creates natural dialogue transcripts, and converts them into high-quality audio podcasts using **LangGraph workflow orchestration**.

## 🎧 **Live Demo**

[Listen to a real podcast](https://soundcloud.com/lfnovo/situational-awareness-podcast) generated with this tool - a 4-person debate on the [Situational Awareness Paper](https://situational-awareness.ai/wp-content/uploads/2024/06/situationalawareness.pdf). Includes my own cloned voice 😂

*Generated using the `diverse_panel` episode profile with 4 AI experts discussing the nuances of artificial general intelligence and situational awareness.*

And [here is a one-speaker version](https://soundcloud.com/lfnovo/single-speaker-podcast-on-situational-awareness) of it, like your real dedicated teacher. 

## 🚀 Quick Start

### Installation

```bash
# Library only (programmatic use)
uv add podcast-creator
# or pip install podcast-creator

# Full installation with web UI
uv add podcast-creator --extra ui
# or pip install podcast-creator[ui]

# Or install from source
git clone <repository-url>
cd podcast-creator
uv sync
# Web UI（Streamlit）需要可选依赖：
uv sync --extra ui
# MCP 服务器（Cursor 等）：pip install -e '.[mcp]' 或 uv sync --extra mcp

# Don't have uv? Install it with:
# curl -LsSf https://astral.sh/uv/install.sh | sh
# or
# pip install uv
```

**Installation Options:**
- **Library only**: `pip install podcast-creator` - For programmatic use without web interface
- **With UI**: `pip install podcast-creator[ui]` - Includes Streamlit web interface for visual management
- **MCP (Cursor / Claude Desktop / other MCP hosts)**: `pip install podcast-creator[mcp]` — exposes stdio tools `podcast_solo`, `podcast_duo`, `podcast_trio` (see [MCP server](#mcp-server-cursor--claude-desktop) below)
- **Doc index** ([`docs/README.md`](docs/README.md)): quick links to MCP, BGM, Streamlit README, changelog

### MCP server (Cursor / Claude Desktop)

Install the extra, then register a **stdio** server that runs `podcast-creator-mcp`:

```bash
uv add 'podcast-creator[mcp]'
# or: pip install 'podcast-creator[mcp]'
```

**Cursor** (`~/.cursor/mcp.json` or project MCP settings): use your interpreter and ensure `podcast-creator` is on that environment’s `PYTHONPATH` if you develop from source.

```json
{
  "mcpServers": {
    "podcast-creator": {
      "command": "podcast-creator-mcp",
      "env": {}
    }
  }
}
```

If the `podcast-creator-mcp` script is not on `PATH`, call the module instead:

```json
{
  "mcpServers": {
    "podcast-creator": {
      "command": "python",
      "args": ["-m", "podcast_creator.mcp_server"]
    }
  }
}
```

**Tools**

| Tool | Episode profile | Use case |
|------|-----------------|----------|
| `podcast_solo` | `solo_expert` | Single-speaker explainer (default providers in bundled profile) |
| `podcast_duo` | `zh_duo_local` or `zh_duo_news_local` | Two-host Chinese; set `duo_style` to `talk` or `news` |
| `podcast_trio` | `zh_trio_local` | Three-host Chinese panel |

Optional **`project_root`**: directory containing `episodes_config.json` and `speakers_config.json` when you use custom profiles. Optional **BGM** uses the same parameters as in [Background music (BGM)](#background-music-bgm).

**macOS + local `uv sync`:** If `podcast-creator ui` fails with `ModuleNotFoundError: No module named 'podcast_creator'`, either editable-install `.pth` files under `.venv/` are missing, **or** they carry the filesystem **hidden** flag (Python 3.11+ skips those and never adds `src/`). **Run from the repo root** (`cd` into `podcast-creator/`), then:

```bash
python3 scripts/fix_venv_pth_macos.py
```

This script **writes** `podcast_creator_repo_src.pth` so **`src/` is prepended to `sys.path`** (via an `import`-style `.pth` line), which avoids a partial **`site-packages/podcast_creator`** shadowing the real package. On macOS it also clears the hidden flag on all `*.pth` files. Alternatively:

```bash
find .venv -name '*.pth' -exec chflags nohidden {} +
```

Verify with `ls -lO .venv/lib/python*/site-packages/_editable*.pth` — the flags column should show `-`, not `hidden`.

**Finder 重复 `.pth`（例如 `distutils-precedence 2.pth`）**：会在启动时执行失败并刷屏 `Error processing line 1 of … _distutils_hack … add_shim`。删掉 `site-packages` 里带 **` 2`** 的那份重复文件（保留无空格的那份），然后重装/修复 `setuptools` 若仍异常。

**损坏的 PyTorch**：若仅在运行 **生成播客**（需要 `esperanto` → `torch`）时崩溃，可尝试在同一 venv 内 `uv pip install --reinstall torch` 或新建干净 venv。

**Workaround without fixing `.pth`:** from repo root,

```bash
PYTHONPATH=src uv run python -m podcast_creator ui
```

Alternatively install a normal (non-editable) wheel: `uv pip install '.[ui]'` (adjust extras as needed).

**Broken Streamlit** (`No module named streamlit.__main__` / “package … cannot be directly executed”): the `streamlit` install under `.venv` may be incomplete—often after an interrupted sync or duplicate trees in `site-packages` (e.g. files ending in ` 2` from Finder). Reinstall:

```bash
uv sync --extra ui --reinstall-package streamlit
# or: pip uninstall -y streamlit && pip install 'streamlit>=1.44.0'
```

### Configure API Keys

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env and add your API keys:
# - OpenAI API key for LLM models
# - ElevenLabs API key for high-quality TTS
# - Other provider keys as needed
```

### Initialize Your Project

```bash
# Create templates and configuration files
podcast-creator init

# This creates:
# - prompts/podcast/outline.jinja
# - prompts/podcast/transcript.jinja  
# - speakers_config.json
# - episodes_config.json
# - example_usage.py
```

### Generate Your First Podcast

#### 🎨 **New: Web Interface**

![Podcast Creator Studio Interface](streamlit.png)

```bash
# Launch the Streamlit web interface
podcast-creator ui

# Custom port/host
podcast-creator ui --port 8080 --host 0.0.0.0

# The UI provides:
# - Visual profile management
# - Multi-content podcast generation  
# - Episode library with playback
# - Import/export functionality
```

#### 🚀 **Episode Profiles (Streamlined)**

```python
import asyncio
from podcast_creator import create_podcast

async def main():
    # One-liner podcast creation with episode profiles!
    result = await create_podcast(
        content="Your content here...",
        episode_profile="tech_discussion",  # 🎯 Pre-configured settings
        episode_name="my_podcast",
        output_dir="output/my_podcast"
    )
    print(f"✅ Podcast created: {result['final_output_file_path']}")

asyncio.run(main())
```

#### 📝 **Classic: Full Configuration**

```python
import asyncio
from podcast_creator import create_podcast

async def main():
    result = await create_podcast(
        content="Your content here...",
        briefing="Create an engaging discussion about...",
        episode_name="my_podcast",
        output_dir="output/my_podcast",
        speaker_config="ai_researchers"
    )
    print(f"✅ Podcast created: {result['final_output_file_path']}")

asyncio.run(main())
```

## 🎯 Episode Profiles - Streamlined Podcast Creation

Episode Profiles are **pre-configured sets of podcast generation parameters** that enable one-liner podcast creation for common use cases while maintaining full customization flexibility.

### 🚀 **Why Episode Profiles?**

- **67% fewer parameters** to specify for common use cases
- **Consistent configurations** across podcast series
- **Faster iteration** and prototyping
- **Team collaboration** with shared settings
- **Full backward compatibility** with existing code

### 📋 **Bundled Profiles**

| Profile | Description | Speakers | Segments | Use Case |
|---------|-------------|----------|----------|----------|
| `tech_discussion` | Technology topics with expert analysis | 2 AI researchers | 4 | Technical content, AI/ML topics |
| `solo_expert` | Educational explanations | 1 expert teacher | 3 | Learning content, tutorials |
| `business_analysis` | Market and business insights | 3 business analysts | 4 | Business strategy, market analysis |
| `diverse_panel` | Multi-perspective discussions | 4 diverse voices | 5 | Complex topics, debate-style content |
| `zh_duo_local` | Chinese two-host dialogue (casual talk) | 2 (主持人 / 嘉宾) | 4 | Local Ollama + Edge TTS; see bundled configs |
| `zh_duo_news_local` | Chinese two-host, news-style tone | 2 (主持人 / 嘉宾) | 4 | Same stack, stricter news briefing |
| `zh_trio_local` | Chinese three-person panel | 3 (主持人 / 乐观派 / 审慎派) | 5 | Roundtable / debate-style |

### Background music (BGM)

After all voice clips are concatenated, you can mix in a **background music** track before final **loudness normalization** (`loudnorm`):

| Parameter | Meaning |
|-----------|---------|
| `bgm_path` | Path to an audio file (e.g. MP3/WAV) readable by pydub/ffmpeg |
| `bgm_mode` | `intro` — BGM only under the opening segment (news-style bed); `full` — BGM under the entire episode |
| `bgm_intro_duration_ms` | Length of the intro BGM window when `bgm_mode=intro` (default in code: 12000) |
| `bgm_gain_db` | Attenuation applied to BGM before mixing (typical −12 to −24; default −20) |

Set these on **`create_podcast()`**, on an **`EpisodeProfile`** in `episodes_config.json`, or (Streamlit) in the generation step’s **optional BGM** fold. Output folder **`metadata.json`** records a `bgm` object when used.

```python
result = await create_podcast(
    content="Your script or source text...",
    episode_profile="zh_duo_local",
    episode_name="episode_with_bed",
    output_dir="output/episode_with_bed",
    bgm_path="/path/to/news-bed.mp3",
    bgm_mode="intro",
    bgm_intro_duration_ms=15000,
    bgm_gain_db=-18.0,
)
```

(requires `ffmpeg` in `PATH` for loudnorm and mix steps, as for normal exports)

### 🎪 **Usage Patterns**

```python
# 1. Simple profile usage
result = await create_podcast(
    content="Your content...",
    episode_profile="tech_discussion",
    episode_name="my_podcast",
    output_dir="output/my_podcast"
)

# 2. Profile with briefing suffix
result = await create_podcast(
    content="Your content...",
    episode_profile="business_analysis",
    briefing_suffix="Focus on ROI and cost optimization",
    episode_name="my_podcast",
    output_dir="output/my_podcast"
)

# 3. Profile with parameter overrides
result = await create_podcast(
    content="Your content...",
    episode_profile="solo_expert",
    outline_model="gpt-4o",  # Override default
    num_segments=5,          # Override default
    episode_name="my_podcast",
    output_dir="output/my_podcast"
)
```

### 🔧 **Custom Episode Profiles**

```python
from podcast_creator import configure

# Define your own episode profiles
configure("episode_config", {
    "profiles": {
        "my_startup_pitch": {
            "speaker_config": "business_analysts",
            "outline_model": "gpt-4o",
            "default_briefing": "Create an engaging startup pitch...",
            "num_segments": 6
        }
    }
})

# Use your custom profile
result = await create_podcast(
    content="Your content...",
    episode_profile="my_startup_pitch",
    episode_name="pitch_deck",
    output_dir="output/pitch_deck"
)
```

## ✨ Features

### 🔧 **Flexible Configuration**

```python
from podcast_creator import configure

# Configure with custom templates
configure("templates", {
    "outline": "Your custom outline template...",
    "transcript": "Your custom transcript template..."
})

# Configure with custom paths
configure({
    "prompts_dir": "./my_templates",
    "speakers_config": "./my_speakers.json",
    "output_dir": "./podcasts"
})

# Configure speakers inline
configure("speakers_config", {
    "profiles": {
        "my_hosts": {
            "tts_provider": "elevenlabs",
            "tts_model": "eleven_flash_v2_5",
            "speakers": [...]
        }
    }
})
```

### 🎙️ **Core Features**

- **🎨 Web Interface**: Complete Streamlit UI for visual podcast creation
- **🎯 Episode Profiles**: Pre-configured settings for one-liner podcast creation
- **🔄 LangGraph Workflow**: Advanced state management and parallel processing
- **🔁 Automatic Retry**: Exponential backoff for transient API failures (LLM & TTS)
- **👥 Multi-Speaker Support**: Dynamic 1-4 speaker configurations with rich personalities
- **⚡ Parallel Audio Generation**: API-safe batching with concurrent processing
- **🔧 Fully Configurable**: Multiple AI providers (OpenAI, Anthropic, Google, etc.)
- **📊 Multi-Content Support**: Combine text, files, and URLs in structured arrays
- **🤖 AI-Powered Generation**: Creates structured outlines and natural dialogues
- **🎵 Multi-Provider TTS**: ElevenLabs, OpenAI, Google TTS support
- **📝 Flexible Templates**: Jinja2-based prompt customization
- **🌍 Multilingual Support**: Generate content in multiple languages
- **🎵 Background music**: Optional intro-only or full-episode BGM mix on the final MP3 (`bgm_path`, `bgm_mode`, …); see [Background music (BGM)](#background-music-bgm)
- **🔌 MCP tools**: Optional `podcast-creator[mcp]` stdio server for `podcast_solo` / `podcast_duo` / `podcast_trio` — [MCP server](#mcp-server-cursor--claude-desktop)
- **📚 Episode Library**: Built-in audio playback and transcript viewing

## 🏗️ Architecture

### Configuration Priority

The library uses a smart priority system for loading resources:

1. **User Configuration** (highest priority)

   ```python
   configure("templates", {"outline": "...", "transcript": "..."})
   ```

2. **Custom Paths**

   ```python
   configure("prompts_dir", "/path/to/templates")
   ```

3. **Working Directory**
   - `./prompts/podcast/*.jinja`
   - `./speakers_config.json`
   - `./episodes_config.json`

4. **Bundled Defaults** (lowest priority)
   - Package includes production-ready templates
   - Multiple speaker profiles included

## 📚 Usage Examples

### 🎯 Episode Profiles (Recommended)

```python
import asyncio
from podcast_creator import create_podcast

# Simple episode profile usage
async def main():
    result = await create_podcast(
        content="AI has transformed many industries...",
        episode_profile="tech_discussion",  # 🚀 One-liner magic!
        episode_name="ai_impact",
        output_dir="output/ai_impact"
    )

asyncio.run(main())
```

### 📝 Classic Configuration

```python
import asyncio
from podcast_creator import create_podcast

async def main():
    result = await create_podcast(
        content="AI has transformed many industries...",
        briefing="Create an informative discussion about AI impact",
        episode_name="ai_impact",
        output_dir="output/ai_impact",
        speaker_config="ai_researchers"
    )

asyncio.run(main())
```

### Advanced Configuration

```python
from podcast_creator import configure, create_podcast

# Custom speaker configuration (with optional per-speaker TTS overrides)
configure("speakers_config", {
    "profiles": {
        "tech_experts": {
            "tts_provider": "elevenlabs",
            "tts_model": "eleven_flash_v2_5",
            "speakers": [
                {
                    "name": "Dr. Alex Chen",
                    "voice_id": "your_voice_id",
                    "backstory": "Senior AI researcher with focus on ethics",
                    "personality": "Thoughtful, asks probing questions"
                },
                {
                    "name": "Jamie Rodriguez",
                    "voice_id": "alloy",
                    "backstory": "Tech journalist and startup advisor",
                    "personality": "Enthusiastic, great at explanations",
                    "tts_provider": "openai",
                    "tts_model": "tts-1"
                }
            ]
        }
    }
})

# Custom templates
configure("templates", {
    "outline": """
    Create a {{ num_segments }}-part podcast outline about: {{ briefing }}
    
    Content: {{ context }}
    
    Speakers: {% for speaker in speakers %}{{ speaker.name }}: {{ speaker.personality }}{% endfor %}
    """,
    "transcript": """
    Generate natural dialogue for: {{ segment.name }}
    
    Keep it conversational and engaging.
    """
})

# Generate podcast with custom configuration
result = await create_podcast(
    content="Your content...",
    briefing="Your briefing...",
    episode_name="custom_podcast",
    speaker_config="tech_experts"
)
```

### 🎪 Episode Profile Variations

```python
# Solo expert explanation
result = await create_podcast(
    content="Technical content...",
    episode_profile="solo_expert",
    episode_name="deep_dive",
    output_dir="output/deep_dive"
)

# Business analysis
result = await create_podcast(
    content="Market trends...",
    episode_profile="business_analysis",
    episode_name="market_analysis",
    output_dir="output/market_analysis"
)

# Panel discussion with diverse perspectives
result = await create_podcast(
    content="Complex topic...",
    episode_profile="diverse_panel",
    episode_name="panel_discussion",
    output_dir="output/panel_discussion"
)
```

### 🔧 Episode Profile Customization

```python
# Use profile with briefing suffix
result = await create_podcast(
    content="Cloud computing trends...",
    episode_profile="business_analysis",
    briefing_suffix="Focus on cost optimization and ROI metrics",
    episode_name="cloud_economics",
    output_dir="output/cloud_economics"
)

# Override specific parameters
result = await create_podcast(
    content="Quantum computing...",
    episode_profile="tech_discussion",
    outline_model="gpt-4o",  # Override default
    num_segments=6,          # Override default
    episode_name="quantum_deep",
    output_dir="output/quantum_deep"
)
```

## 🔧 Configuration API

### Main Functions

```python
from podcast_creator import configure, get_config, create_podcast

# Set configuration
configure(key, value)
configure({"key1": "value1", "key2": "value2"})

# Get configuration
value = get_config("key", default_value)

# Generate podcast
result = await create_podcast(...)
```

### Configuration Options

| Key | Type | Description |
|-----|------|-------------|
| `prompts_dir` | `str` | Directory containing template files |
| `templates` | `dict` | Inline template content |
| `speakers_config` | `str/dict` | Path to speaker JSON or inline config |
| `episode_config` | `str/dict` | Path to episode JSON or inline config |
| `output_dir` | `str` | Default output directory |

## 🎭 Speaker Configuration

### Speaker Profile Structure

```json
{
  "profiles": {
    "profile_name": {
      "tts_provider": "elevenlabs",
      "tts_model": "eleven_flash_v2_5",
      "speakers": [
        {
          "name": "Speaker Name",
          "voice_id": "voice_id_from_provider",
          "backstory": "Rich background that informs expertise",
          "personality": "Speaking style and traits"
        }
      ]
    }
  }
}
```

### Per-Speaker TTS Overrides

Individual speakers can override the profile-level TTS provider, model, and config. This lets you mix different TTS services within the same podcast — for example, one speaker on ElevenLabs and another on OpenAI TTS.

```json
{
  "profiles": {
    "mixed_providers": {
      "tts_provider": "openai",
      "tts_model": "tts-1",
      "speakers": [
        {
          "name": "Dr. Sarah Chen",
          "voice_id": "custom_eleven_voice_id",
          "backstory": "AI researcher...",
          "personality": "Analytical and methodical",
          "tts_provider": "elevenlabs",
          "tts_model": "eleven_flash_v2_5",
          "tts_config": { "voice_settings": { "stability": 0.8 } }
        },
        {
          "name": "Marcus Rivera",
          "voice_id": "alloy",
          "backstory": "Tech journalist...",
          "personality": "Engaging and curious"
        }
      ]
    }
  }
}
```

In this example, Dr. Sarah Chen uses ElevenLabs while Marcus Rivera uses the profile-level OpenAI TTS. All three fields (`tts_provider`, `tts_model`, `tts_config`) are optional per speaker — any field not set falls back to the profile-level value. If a speaker defines `tts_config`, it **replaces** the profile-level config entirely (no merging).

### Creating Custom Speakers

1. **Get Voice IDs** from your TTS provider
2. **Design Personalities** that complement each other
3. **Write Rich Backstories** to guide content expertise
4. **Test Combinations** with different content types

## 🌐 Supported Providers

### Language Models (via Esperanto)

- **OpenAI**: GPT-4, GPT-4o, o1, o3
- **Anthropic**: Claude 3.5 Sonnet, Claude 3 Opus
- **Google**: Gemini Pro, Gemini Flash
- **Groq**: Mixtral, Llama models
- **Ollama**: Local model support
- **Perplexity**: Research-enhanced models
- **Azure OpenAI**: Enterprise OpenAI
- **Mistral**: Mistral models
- **DeepSeek**: DeepSeek models
- **xAI**: Grok models
- **OpenRouter**: Multi-provider access

### Text-to-Speech Services

- **ElevenLabs**: Professional voice synthesis
- **OpenAI TTS**: High-quality voices
- **Google**: Google Cloud TTS
- **Vertex AI**: Google Cloud enterprise
- **Piper**: Local offline TTS (via `piper` binary)
- **Coqui TTS**: Local Python-based TTS (`coqui-tts`)

### Local TTS and Fallback

You can now route TTS through a provider abstraction and configure fallback in `tts_config`.

```json
{
  "profiles": {
    "local_first": {
      "tts_provider": "coqui",
      "tts_model": "tts_models/en/ljspeech/tacotron2-DDC",
      "tts_config": {
        "gpu": false,
        "fallback_provider": "piper",
        "fallback_model": "zh_CN-huayan-medium.onnx",
        "fallback_config": {
          "piper_bin": "piper",
          "model_path": "zh_CN-huayan-medium.onnx"
        }
      },
      "speakers": [
        {
          "name": "Host",
          "voice_id": "alloy",
          "backstory": "Generalist host",
          "personality": "Warm and concise"
        }
      ]
    }
  }
}
```

`none` provider is also supported for script-only workflows (no audio generation).

### 多人中文对话（Edge TTS）

仓库内已预置：

- **说话人**：`speakers_config.json` 中 `zh_duo_talk_edge`（2 人：主持人 / 嘉宾）、`zh_duo_news_edge`（双人新闻串联语感，与 `zh_hq_news_edge` 相同的 `rate`/`pitch`/`volume`，主持人 Yunjian + 嘉宾 Xiaoxiao）、`zh_trio_panel_edge`（3 人圆桌）。
- **剧集**：`episodes_config.json` 中 `zh_duo_local`、`zh_duo_news_local`（新闻感双人）、`zh_trio_local`，已写好要求 LLM **严格使用上述姓名** 生成对白的 `default_briefing`。

使用方式：生成时选择对应 **剧集 profile**（或通过 API `episode_profile="zh_duo_local"` 等）。每位说话人使用不同 `voice_id`（Edge 神经音色名），合成时按角色自动选声线。

## 📁 Output Structure

```text
output/episode_name/
├── outline.json          # Structured outline
├── transcript.json       # Complete dialogue
├── clips/               # Individual audio clips
│   ├── 0000.mp3         # First segment
│   ├── 0001.mp3         # Second segment
│   └── ...              # Additional segments
└── audio/               # Final output
    └── episode_name.mp3  # Complete podcast
```

## 🛠️ CLI Commands

```bash
# Launch web interface (requires UI installation)
podcast-creator ui

# Launch on custom port/host
podcast-creator ui --port 8080 --host 0.0.0.0

# Skip dependency check
podcast-creator ui --skip-init-check

# Initialize project with templates
podcast-creator init

# Initialize in specific directory
podcast-creator init --output-dir /path/to/project

# Overwrite existing files
podcast-creator init --force

# Show version
podcast-creator version
```

**Note**: The `ui` command requires the UI installation: `pip install podcast-creator[ui]`

### Deck-AV CLI (`podcast_deck`)

The repository also includes a deck/video pipeline CLI under `podcast_deck`:

```bash
# Step-by-step: capture frames
uv run python -m podcast_deck capture-frames \
  --input output/decks/p3-e2e/deck.json \
  --workspace output/decks/p3-e2e/workspace \
  --fps 10 --hold-sec 1.0 --transition-sec 0.5

# Step-by-step: render video (optional subtitle/audio)
uv run python -m podcast_deck render-video \
  --workspace output/decks/p3-e2e/workspace \
  --output-mp4 output/decks/p3-e2e/workspace/deck.final.mp4 \
  --subtitle-mode burn \
  --audio output/decks/p3-e2e/workspace/narration.test.wav

# One-shot pipeline: capture + render
uv run python -m podcast_deck synth-video \
  --input output/decks/p3-e2e/deck.json \
  --workspace output/decks/p3-e2e/synth-workspace \
  --fps 10 --hold-sec 1.0 --transition-sec 0.5 \
  --subtitle-mode burn \
  --audio output/decks/p3-e2e/workspace/narration.test.wav \
  --output-mp4 output/decks/p3-e2e/synth-workspace/deck.synth.mp4

# One-shot pipeline + cleanup intermediates
uv run python -m podcast_deck synth-video \
  --input output/decks/p3-e2e/deck.json \
  --workspace output/decks/p3-e2e/synth-clean-workspace \
  --subtitle-mode burn \
  --audio output/decks/p3-e2e/workspace/narration.test.wav \
  --output-mp4 output/decks/p3-e2e/synth-clean-workspace/deck.synth.clean.mp4 \
  --clean-workspace
```

`render-video` / `synth-video` subtitle behavior:
- Prefer ffmpeg `subtitles` filter (external or auto-generated SRT)
- Fallback to `drawtext` when `subtitles` is unavailable
- If both subtitle filters are unavailable in local ffmpeg build, continue rendering without subtitle filter (pipeline remains usable)

`synth-video` workspace behavior:
- Default `--keep-frames`: keep `frames/`, `slides/`, and `frame_manifest.json` for debugging/re-renders
- Optional `--clean-workspace`: remove intermediate artifacts after successful render (keep final MP4 only)

### 🎨 Web Interface Features

The `podcast-creator ui` command launches a comprehensive Streamlit interface that provides:

- **🏠 Dashboard**: Statistics and quick actions
- **🎙️ Speaker Management**: Visual profile creation with voice selection dropdowns
- **📺 Episode Management**: Configure generation parameters and AI models
- **🎬 Podcast Generation**: Multi-content support (text, files, URLs) with real-time progress
- **📚 Episode Library**: Audio playback, transcript viewing, and downloads
- **📤 Import/Export**: Share profiles via JSON files

The interface automatically detects missing dependencies and offers to run initialization if needed.

## 🚀 Performance

- **⚡ Parallel Processing**: 5 concurrent audio clips per batch (configurable)
- **🔄 API-Safe Batching**: Respects provider rate limits
- **📊 Scalable**: Handles 30+ dialogue segments efficiently
- **⏱️ Fast Generation**: ~2-3 minutes for typical podcasts
- **🎯 Optimized Workflow**: Smart resource management

### ⚠️ Rate Limiting Configuration

If you encounter errors like `ElevenLabs API error: Too many concurrent requests`, you can adjust the parallel processing batch size:

```bash
# In your .env file
TTS_BATCH_SIZE=2  # Reduce from default 5 to 2 for ElevenLabs free plan
```

This is particularly useful for:
- **ElevenLabs Free Plan**: Limited to 2 concurrent requests
- **Other TTS providers** with stricter rate limits
- **Debugging**: Set to 1 for sequential processing

### 🔁 Retry Configuration

LLM and TTS API calls automatically retry on transient failures (network errors, timeouts, rate limits) with exponential backoff. Non-retryable errors are raised immediately without retry — this includes programming errors (e.g. `ValueError`) and HTTP 4xx client errors (e.g. 404 model not found, 401 auth failure), except 429 rate-limit which is retried.

```bash
# In your .env file
PODCAST_RETRY_MAX_ATTEMPTS=3       # Max retry attempts (default: 3)
PODCAST_RETRY_WAIT_MULTIPLIER=5    # Backoff multiplier in seconds (default: 5)
PODCAST_RETRY_WAIT_MAX=30          # Max wait between retries in seconds (default: 30)
```

You can also configure retries programmatically for LLM calls (outline and transcript generation):

```python
result = await create_podcast(
    content="Your content...",
    episode_profile="tech_discussion",
    episode_name="my_podcast",
    output_dir="output/my_podcast",
    retry_max_attempts=5,        # Override default
    retry_wait_multiplier=3,     # Override default
)
```

To disable retries entirely, set `PODCAST_RETRY_MAX_ATTEMPTS=1`.

### 🌐 Proxy Configuration

If you're behind a corporate firewall or need to route requests through a proxy, use standard environment variables:

```bash
# In your .env file or shell environment
HTTP_PROXY=http://proxy.example.com:8080
HTTPS_PROXY=http://proxy.example.com:8080
NO_PROXY=localhost,127.0.0.1
```

**Authenticated Proxies:**

```bash
# Proxies with authentication are supported
HTTP_PROXY=http://user:password@proxy.example.com:8080
HTTPS_PROXY=http://user:password@proxy.example.com:8080
```

The underlying libraries (esperanto, content-core) automatically detect and use these standard proxy environment variables for all network requests.

## 🧪 Development

### Installing for Development

```bash
git clone <repository-url>
cd podcast-creator

# Install with uv (recommended)
uv sync

# This installs the package in editable mode
# along with all dependencies
```

### Project Structure

```text
podcast-creator/
├── src/
│   └── podcast_creator/
│       ├── __init__.py           # Public API
│       ├── config.py             # Configuration system
│       ├── cli.py                # CLI commands (with UI command)
│       ├── core.py               # Core utilities
│       ├── graph.py              # LangGraph workflow
│       ├── nodes.py              # Workflow nodes
│       ├── retry.py              # Retry utilities with exponential backoff
│       ├── speakers.py           # Speaker management
│       ├── episodes.py           # Episode profile management
│       ├── state.py              # State management
│       ├── validators.py         # Validation utilities
│       └── resources/            # Bundled templates
│           ├── prompts/
│           ├── speakers_config.json
│           ├── episodes_config.json
│           ├── streamlit_app/    # Web interface
│           └── examples/
├── pyproject.toml               # Package configuration
└── README.md
```

### Testing

```bash
# Test the package
python -c "from podcast_creator import create_podcast; print('Import successful')"

# Test CLI
podcast-creator --help

# Test web interface
podcast-creator ui

# Test initialization
mkdir test_project
cd test_project
podcast-creator init
python example_usage.py
```

## 📝 Examples

Check the `examples/` directory for:

- **Episode Profiles**: Comprehensive guide to streamlined podcast creation
- Basic usage examples
- Advanced configuration
- Custom speaker setups
- Multi-language podcasts
- Different content types

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details on:

- 🚀 Getting started with development
- 📋 Our pull request process  
- 🧪 Testing guidelines
- 🎨 Code style and standards
- 🐛 How to report bugs
- 💡 How to suggest new features

Quick links:
- [Good First Issues](https://github.com/lfnovo/podcast-creator/labels/good%20first%20issue)
- [Contributing Guide](CONTRIBUTING.md)
- [Report a Bug](https://github.com/lfnovo/podcast-creator/issues/new?template=bug_report.md)
- [Request a Feature](https://github.com/lfnovo/podcast-creator/issues/new?template=feature_request.md)

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](https://github.com/lfnovo/podcast-creator/blob/main/LICENSE) file for details.

## 🔗 Links

- **Examples**: [Examples](https://github.com/lfnovo/podcast-creator/tree/main/examples)

---

Made with ❤️ for the AI community
