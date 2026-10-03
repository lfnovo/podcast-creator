# Maintainer profile — scope and tone

## What we own

- The `podcast-creator` Python library (`src/podcast_creator/`) and its public API
  (`create_podcast()` and exports).
- The CLI (`podcast-creator init|ui|version`) and the Streamlit UI.
- The bundled prompt templates, speaker profiles and episode profiles.

## What we do not own

- esperanto (lfnovo/esperanto): provider abstraction for LLM and TTS calls.
- content-core and ai-prompter.
- AI providers and self-hosted TTS servers (e.g. Speaches, Kokoro).
- Open Notebook (lfnovo/open-notebook), a consumer of this library.

## Tone in public text

- Answer first; no filler and no marketing.
- Say what was verified in the code, separately from opinion.
- No promises of timelines.

## Never cite in public

- Contents of `specs/` and `CLAUDE.local.md` (gitignored, private).
