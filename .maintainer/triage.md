# Triage rules

Repository-specific rules layered over the plugin's maturity-ladder preset. They refine the
preset; they never contradict it silently.

## Extra labels and their meaning

- The existing labels (`bug`, `enhancement`, `documentation`, `question`, `good first issue`,
  `help wanted`, `duplicate`, `invalid`, `wontfix`) describe the kind of issue, not its
  pipeline state. Triage never adds or removes them.

## Close criteria particular to this project

- Many issues are relayed from Open Notebook (lfnovo/open-notebook), which consumes this
  library. Before accepting one, check whether the root cause lives here or in a dependency
  or consumer: esperanto (provider calls, TTS), the TTS server itself (e.g. Speaches/Kokoro),
  or Open Notebook not passing an option this library already exposes. Close or redirect
  when the cause is outside this repository.
- Before calling a limit "hardcoded", check whether `create_podcast()` or the episode profile
  already overrides it (e.g. `outline_config` / `transcript_config`).

## Areas and owners

- Audio assembly: `src/podcast_creator/core.py` (`combine_audio_files`), `generate_all_audio`.
- LLM generation and parsing: `src/podcast_creator/nodes.py`, `core.py` parsers, `prompts/`.
- Configuration and profiles: `config.py`, `episodes.py`, `speakers.py`, `resources/*.json`.
- Retry: `retry.py`.
- CLI and UI: `cli.py`, `resources/streamlit_app/`.
- Owner: lfnovo.

## Vision-fit heuristics

- `README.md` and `AGENTS.md` define the scope: a library that turns content into a
  conversational podcast through a LangGraph pipeline, provider-agnostic via esperanto.
- Infrastructure integrations (storage backends, hosting, distribution) stay outside the
  core; callers get a local file path and handle the rest.
- Requests without concrete demand are closed with an open door rather than parked.
