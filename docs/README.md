# Podcast Creator — documentation index

Canonical user-facing documentation lives in the **repository root [README.md](../README.md)**. This page links the main topics.

| Topic | Where |
|--------|--------|
| Install (library, UI, MCP) | [README — Quick Start / Installation](../README.md#-quick-start) |
| MCP server (Cursor, Claude Desktop, `podcast-creator-mcp`) | [README — MCP server](../README.md#mcp-server-cursor--claude-desktop) |
| Background music (`intro` / `full`, paths, gain) | [README — Background music (BGM)](../README.md#background-music-bgm) |
| Episode profiles (bundled + custom) | [README — Episode Profiles](../README.md#-episode-profiles---streamlined-podcast-creation) |
| macOS editable `.venv` / `ModuleNotFoundError` | [README — Installation (macOS / `.pth`)](../README.md#installation) |
| Streamlit Studio (UI features, BGM in-app) | [src/podcast_creator/resources/streamlit_app/README.md](../src/podcast_creator/resources/streamlit_app/README.md) |
| GPT-SoVITS（参考音频 / 本地 API） | [docs/gpt-sovits.md](gpt-sovits.md) |
| Voicebox（`POST /generate` + `GET /audio/{id}`） | [docs/voicebox.md](voicebox.md) |
| Deck AV Epic 任务拆分（Epic/Story/里程碑） | [docs/deck-epic-story-breakdown.md](deck-epic-story-breakdown.md) |
| Changelog | [CHANGELOG.md](../CHANGELOG.md) |
| Contributor / dev commands | [CONTRIBUTING.md](../CONTRIBUTING.md), [CLAUDE.md](../CLAUDE.md) |

Agent implementers: for MCP entrypoints and graph/BGM hook details, use **CLAUDE.md** as the source of truth.
