"""Turn grouping and saved group plans; synthesis remains Esperanto's job."""

import json
from pathlib import Path
from typing import List, Sequence

from .core import Dialogue


def format_dialogue(turns: Sequence[Dialogue]) -> str:
    """Keep each turn on one line for Esperanto's speaker-name parser."""
    return "\n".join(
        f"{turn.speaker}: {' '.join(turn.dialogue.splitlines()).strip()}"
        for turn in turns
    )


def group_dialogue(
    turns: Sequence[Dialogue],
    max_chars: int,
    section_starts: Sequence[int] = (),
) -> List[List[Dialogue]]:
    """Prefer known section boundaries, then speaker changes, then whole turns.

    Section starts are zero-based transcript indices. The transcript generator
    currently drops section provenance, so callers must supply it when known.
    A fitting remainder stays together, including a whole-episode single group.
    Oversized turns fail before any requests rather than being split or truncated.
    """
    if max_chars < 1:
        raise ValueError("max_chars must be positive")
    boundaries = set(section_starts)
    if any(
        type(index) is not int or not 0 <= index < len(turns) for index in boundaries
    ):
        raise ValueError("section_starts must contain valid zero-based turn indices")
    lengths = [len(format_dialogue([turn])) for turn in turns]
    for index, length in enumerate(lengths):
        if length > max_chars:
            raise ValueError(
                f"Turn {index} is {length} characters, exceeding the provider's "
                f"{max_chars}-character group budget; shorten this turn"
            )
    groups = []
    start = 0
    while start < len(turns):
        end, size = start, 0
        while end < len(turns):
            added = lengths[end] + (1 if end > start else 0)
            if size + added > max_chars:
                break
            size += added
            end += 1
        if end < len(turns):
            sections = [i for i in boundaries if start < i <= end]
            changes = [
                i
                for i in range(start + 1, end + 1)
                if turns[i - 1].speaker != turns[i].speaker
            ]
            end = max(sections) if sections else max(changes, default=end)
        groups.append(list(turns[start:end]))
        start = end
    return groups


def save_group_plan(output_dir: Path, groups, profile) -> None:
    """Save exact group membership for regeneration, without credentials/config."""
    output_dir.mkdir(parents=True, exist_ok=True)
    plan = {
        "version": 1,
        "tts_provider": profile.tts_provider,
        "tts_model": profile.tts_model,
        "voices": profile.get_voice_mapping(),
        "groups": [[turn.model_dump() for turn in group] for group in groups],
    }
    temporary = output_dir / "audio_groups.json.tmp"
    temporary.write_text(
        json.dumps(plan, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    temporary.replace(output_dir / "audio_groups.json")
