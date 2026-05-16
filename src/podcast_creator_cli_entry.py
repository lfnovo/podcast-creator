"""
Top-level console entry (copied to site-packages root by the wheel).

``podcast-creator`` points here so the interpreter can run without an editable
install or ``.pth``: we locate ``<repo>/src`` (typical layout ``repo/.venv``)
and prepend it to ``sys.path`` before importing ``podcast_creator.cli``.
"""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path


def _ensure_src_on_path() -> None:
    if importlib.util.find_spec("podcast_creator") is not None:
        return

    def try_insert(src_root: Path) -> bool:
        src_root = src_root.resolve()
        if not (src_root / "podcast_creator" / "__init__.py").is_file():
            return False
        s = str(src_root)
        if s not in sys.path:
            sys.path.insert(0, s)
        return True

    raw = os.environ.get("PODCAST_CREATOR_REPO_ROOT", "").strip()
    if raw and try_insert(Path(raw) / "src"):
        return

    # repo/.venv/bin/python -> repo/src
    exe = Path(sys.executable).resolve()
    if try_insert(exe.parent.parent.parent / "src"):
        return

    here = Path.cwd().resolve()
    for base in (here, *here.parents):
        if try_insert(base / "src"):
            return


def main() -> None:
    _ensure_src_on_path()
    from podcast_creator.cli import cli

    cli()


def mcp_main() -> None:
    _ensure_src_on_path()
    try:
        from podcast_creator.mcp_server import main as mcp_run
    except ModuleNotFoundError as exc:
        missing = getattr(exc, "name", "") or "mcp"
        raise SystemExit(
            "MCP entrypoint requires optional dependency support. "
            "Install with: `uv pip install \"podcast-creator[mcp]\"` "
            f"(missing: {missing})"
        ) from exc

    mcp_run()


if __name__ == "__main__":
    main()
