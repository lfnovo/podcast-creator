"""CLI for HTML deck export."""

from __future__ import annotations

from pathlib import Path

import click

from .exporter import DeckBuildOptions, export_deck
from .schema import DeckSchemaError


@click.group()
def cli() -> None:
    """Podcast deck tools."""


@cli.command("export")
@click.option(
    "--input",
    "input_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    required=True,
    help="Path to deck/outline JSON file.",
)
@click.option(
    "--output",
    "output_path",
    type=click.Path(dir_okay=False, path_type=Path),
    required=True,
    help="Path to output single-file HTML.",
)
@click.option(
    "--debug-script",
    is_flag=True,
    default=False,
    help="Include debug script block in HTML (for local debug builds only).",
)
@click.option(
    "--aspect-ratio",
    type=click.Choice(["16:9", "4:3"], case_sensitive=False),
    default="16:9",
    show_default=True,
    help="Deck aspect ratio.",
)
def export_cmd(
    input_path: Path, output_path: Path, debug_script: bool, aspect_ratio: str
) -> None:
    """Export deck JSON to single-file HTML."""
    try:
        result = export_deck(
            input_path=input_path,
            output_path=output_path,
            options=DeckBuildOptions(
                debug_script_enabled=debug_script, aspect_ratio=aspect_ratio
            ),
        )
        size = result.stat().st_size
        click.echo(f"✅ Deck exported: {result} ({size} bytes)")
    except DeckSchemaError as exc:
        raise click.ClickException(f"Schema validation failed: {exc}") from exc
    except Exception as exc:  # pragma: no cover - defensive boundary
        raise click.ClickException(str(exc)) from exc


def main() -> None:
    """Console entry for module execution."""
    cli()
