"""CLI commands for podcast-creator package."""

import shutil
from pathlib import Path
from typing import Optional

import click
from loguru import logger


def copy_resource_file(
    source_path: str, target_path: Path, description: str
) -> bool:
    """
    Copy a resource file from package to target location.

    Args:
        source_path: Path to source file within package resources
        target_path: Target file path
        description: Description for logging

    Returns:
        True if file was copied, False if it already exists
    """
    if target_path.exists():
        click.echo(f"✓ {description} already exists: {target_path}")
        return False

    try:
        import importlib.resources as resources

        # Load resource content
        package_resources = resources.files("podcast_creator.resources")
        resource = package_resources.joinpath(source_path)

        if resource.is_file():
            # Ensure parent directory exists
            target_path.parent.mkdir(parents=True, exist_ok=True)

            # Copy content
            content = resource.read_text()
            target_path.write_text(content)

            click.echo(f"✓ Created {description}: {target_path}")
            return True
        else:
            click.echo(f"✗ Resource not found: {source_path}")
            return False

    except Exception as e:
        click.echo(f"✗ Error copying {description}: {e}")
        return False


@click.group()
@click.version_option()
def cli():
    """Podcast Creator - AI-powered podcast generation tool."""
    pass


@cli.command()
@click.option(
    "--force",
    is_flag=True,
    help="Overwrite existing files",
)
@click.option(
    "--output-dir",
    type=click.Path(),
    default=".",
    help="Output directory for initialization (default: current directory)",
)
def init(force: bool, output_dir: str) -> None:
    """
    Initialize podcast creator templates and configuration.

    This command creates the following files in the specified directory:
    - prompts/podcast/outline.jinja
    - prompts/podcast/transcript.jinja
    - speakers_config.json
    - example_usage.py

    These files provide a starting point for podcast generation and can be
    customized according to your needs.
    """
    output_path = Path(output_dir).resolve()

    click.echo(f"🎙️ Initializing podcast creator in: {output_path}")

    # Check if output directory exists
    if not output_path.exists():
        output_path.mkdir(parents=True, exist_ok=True)
        click.echo(f"✓ Created output directory: {output_path}")

    # Files to copy
    files_to_copy = [
        {
            "source": "prompts/podcast/outline.jinja",
            "target": output_path / "prompts" / "podcast" / "outline.jinja",
            "description": "outline template",
        },
        {
            "source": "prompts/podcast/transcript.jinja",
            "target": output_path / "prompts" / "podcast" / "transcript.jinja",
            "description": "transcript template",
        },
        {
            "source": "speakers_config.json",
            "target": output_path / "speakers_config.json",
            "description": "speaker configuration",
        },
        {
            "source": "examples/example_usage.py",
            "target": output_path / "example_usage.py",
            "description": "example usage script",
        },
    ]

    # Track results
    copied_files = 0
    existing_files = 0
    failed_files = 0

    for file_info in files_to_copy:
        source = file_info["source"]
        target = file_info["target"]
        description = file_info["description"]

        # Check if file exists and force flag
        if target.exists():
            if force:
                click.echo(f"⚠ Overwriting existing {description}: {target}")
                target.unlink()  # Remove existing file
            else:
                existing_files += 1
                continue

        # Copy the file
        success = copy_resource_file(source, target, description)
        if success:
            copied_files += 1
        else:
            failed_files += 1

    # Summary
    click.echo(f"\n📊 Initialization Summary:")
    click.echo(f"   ✓ Files copied: {copied_files}")
    if existing_files > 0:
        click.echo(f"   → Files already exist: {existing_files}")
    if failed_files > 0:
        click.echo(f"   ✗ Files failed: {failed_files}")

    if failed_files == 0:
        click.echo(f"\n🎉 Initialization complete!")
        click.echo(f"\nNext steps:")
        click.echo(f"1. Customize templates in: {output_path}/prompts/")
        click.echo(f"2. Modify speaker configuration: {output_path}/speakers_config.json")
        click.echo(f"3. Run the example: python {output_path}/example_usage.py")
        click.echo(f"\n📖 Documentation: https://github.com/lfnovo/podcast-creator")
    else:
        click.echo(f"\n⚠ Some files could not be created. Please check the errors above.")

    if existing_files > 0 and not force:
        click.echo(f"\n💡 Tip: Use --force to overwrite existing files")


@cli.command()
def version():
    """Show version information."""
    try:
        from . import __version__

        click.echo(f"podcast-creator {__version__}")
    except ImportError:
        click.echo("podcast-creator (version unknown)")


if __name__ == "__main__":
    cli()