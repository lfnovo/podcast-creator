"""Shared default values (kept dependency-free to avoid import cycles)."""

# Silence inserted between consecutive clips when combining audio
DEFAULT_AUDIO_GAP_MS = 400


def validate_audio_gap_ms(value: object) -> int:
    """Return value if it is a non-negative int (bools excluded); raise ValueError otherwise."""
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"audio_gap_ms must be a non-negative integer, got {value!r}")
    return value
