# .maintainer

Maintainer profile read by the [oss-maintainer](https://github.com/lfnovo/oss-maintainer)
plugin for Claude Code and Codex. It holds what the maintenance workflows of this repository
need and cannot derive. It is not a list of people; see `MAINTAINERS` or `GOVERNANCE.md`.

Each fact has one home: executable commands live in the `Makefile` or `AGENTS.md` and are
referenced, never copied; `profile.toml` holds the fields the plugin reads; `release/runbook.md`
holds the release sequence and policy; `gotchas.md` holds the lessons. Other files link to
those instead of repeating them.

| File | Purpose |
|---|---|
| `profile.toml` | the fields the plugin reads (schema v1) |
| `PROFILE.md` | scope, tone, what must never be cited in public |
| `gotchas.md` | fragile areas and known issues, fed by release retros |
| `triage.md` | triage rules specific to this repository |
| `release/runbook.md` | the release sequence and policy |
| `release/test-matrix.md` | the recurring risks, seed of each release's coverage table |
| `smoke/journey.md` | the product journey the smoke test executes (applications only) |
| `decisions.md` | append-only log of decisions (optional) |
| `profile.local.toml` | gitignored local preferences |
| `state/` | gitignored run records and reports |
