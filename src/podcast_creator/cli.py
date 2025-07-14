"""CLI commands for podcast-creator package."""

from pathlib import Path

import click
import os
import subprocess
import sys


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
    help="Overwrite existing files without prompting",
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
    - episodes_config.json
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
            "source": "episodes_config.json",
            "target": output_path / "episodes_config.json",
            "description": "episode configuration",
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
    skipped_files = 0
    
    # State for "all" choices
    overwrite_all = False
    skip_all = False

    for file_info in files_to_copy:
        source = file_info["source"]
        target = file_info["target"]
        description = file_info["description"]

        # Check if file exists
        if target.exists():
            should_overwrite = False
            
            if force or overwrite_all:
                should_overwrite = True
            elif skip_all:
                should_overwrite = False
            else:
                # Ask user for this specific file
                click.echo(f"\n📄 File already exists: {target}")
                choice = click.prompt(
                    f"Overwrite {description}? [y]es, [n]o, [a]ll, [s]kip all",
                    type=click.Choice(['y', 'n', 'a', 's'], case_sensitive=False),
                    default='n'
                )
                
                if choice == 'y':
                    should_overwrite = True
                elif choice == 'n':
                    should_overwrite = False
                elif choice == 'a':
                    should_overwrite = True
                    overwrite_all = True
                elif choice == 's':
                    should_overwrite = False
                    skip_all = True
            
            if should_overwrite:
                click.echo(f"⚠ Overwriting existing {description}: {target}")
                target.unlink()  # Remove existing file
            else:
                existing_files += 1
                skipped_files += 1
                click.echo(f"→ Skipped existing {description}: {target}")
                continue

        # Copy the file
        success = copy_resource_file(source, target, description)
        if success:
            copied_files += 1
        else:
            failed_files += 1

    # Summary
    click.echo("\n📊 Initialization Summary:")
    click.echo(f"   ✓ Files copied: {copied_files}")
    if skipped_files > 0:
        click.echo(f"   → Files skipped: {skipped_files}")
    if failed_files > 0:
        click.echo(f"   ✗ Files failed: {failed_files}")

    if failed_files == 0:
        click.echo("\n🎉 Initialization complete!")
        click.echo("\nNext steps:")
        click.echo(f"1. Customize templates in: {output_path}/prompts/")
        click.echo(f"2. Modify speaker configuration: {output_path}/speakers_config.json")
        click.echo(f"3. Modify episode configuration: {output_path}/episodes_config.json")
        click.echo(f"4. Run the example: python {output_path}/example_usage.py")
        click.echo("\n📖 Documentation: https://github.com/lfnovo/podcast-creator")
    else:
        click.echo("\n⚠ Some files could not be created. Please check the errors above.")

    if skipped_files > 0 and not force:
        click.echo("\n💡 Tip: Use --force to overwrite all existing files without prompting")


@cli.command()
def version():
    """Show version information."""
    try:
        from . import __version__

        click.echo(f"podcast-creator {__version__}")
    except ImportError:
        click.echo("podcast-creator (version unknown)")


def check_dependencies_and_init() -> bool:
    """
    Check if required directories exist and offer to run init if not.
    
    Returns:
        True if dependencies are satisfied, False otherwise
    """
    current_dir = Path.cwd()
    prompts_dir = current_dir / "prompts"
    speakers_config = current_dir / "speakers_config.json"
    episodes_config = current_dir / "episodes_config.json"
    
    missing_items = []
    
    if not prompts_dir.exists():
        missing_items.append("prompts directory")
    
    if not speakers_config.exists():
        missing_items.append("speakers_config.json")
        
    if not episodes_config.exists():
        missing_items.append("episodes_config.json")
    
    if not missing_items:
        return True
    
    click.echo("🚨 Missing required files/directories:")
    for item in missing_items:
        click.echo(f"   ✗ {item}")
    
    click.echo(f"\nTo use the UI, you need to initialize podcast-creator in this directory.")
    
    if click.confirm("Would you like to run 'podcast-creator init' now?"):
        click.echo("\n🔄 Running initialization...")
        
        # Run init command
        from click.testing import CliRunner
        runner = CliRunner()
        result = runner.invoke(init, ['--output-dir', str(current_dir)])
        
        if result.exit_code == 0:
            click.echo("✅ Initialization completed successfully!")
            return True
        else:
            click.echo("❌ Initialization failed!")
            click.echo(result.output)
            return False
    else:
        click.echo("\n💡 Run 'podcast-creator init' manually to set up required files.")
        return False


@cli.command()
@click.option(
    "--port",
    type=int,
    default=8501,
    help="Port to run Streamlit app on (default: 8501)",
)
@click.option(
    "--host",
    type=str,
    default="localhost",
    help="Host to run Streamlit app on (default: localhost)",
)
@click.option(
    "--skip-init-check",
    is_flag=True,
    help="Skip initialization check and start UI directly",
)
def ui(port: int, host: str, skip_init_check: bool) -> None:
    """
    Launch the Streamlit web interface for Podcast Creator.
    
    This command starts a web-based interface that provides:
    - Speaker and episode profile management
    - Podcast generation with content upload
    - Episode library and playback
    - Profile import/export functionality
    
    The UI requires initialization files in the current directory.
    Use --skip-init-check to bypass the dependency check.
    """
    # Check if Streamlit is available
    try:
        import streamlit
    except ImportError:
        click.echo("❌ Streamlit is not installed. The UI feature requires Streamlit.")
        click.echo()
        click.echo("Install options:")
        click.echo("  • Full installation: pip install podcast-creator[ui]")
        click.echo("  • Streamlit only:    pip install streamlit>=1.46.1")
        click.echo()
        click.echo("💡 For library-only usage without UI, no additional installation needed.")
        sys.exit(1)
    
    current_dir = Path.cwd()
    
    # Check dependencies unless skipped
    if not skip_init_check:
        click.echo("🔍 Checking dependencies...")
        if not check_dependencies_and_init():
            click.echo("\n❌ Cannot start UI without required files.")
            sys.exit(1)
        
        click.echo("✅ All dependencies satisfied!")
    
    # Find the streamlit app file
    try:
        import importlib.resources as resources
        package_resources = resources.files("podcast_creator")
        
        # Check if we have a bundled streamlit app
        app_file = None
        try:
            streamlit_resources = package_resources / "resources" / "streamlit_app"
            app_resource = streamlit_resources / "app.py"
            if app_resource.is_file():
                # Extract to temp directory for execution
                import tempfile
                import shutil
                
                temp_dir = Path(tempfile.mkdtemp(prefix="podcast-creator-ui-"))
                
                # Copy the entire streamlit_app directory
                def copy_resource_dir(source_path, target_dir):
                    """Recursively copy resource directory."""
                    target_dir.mkdir(parents=True, exist_ok=True)
                    
                    for item in source_path.iterdir():
                        if item.is_file():
                            try:
                                # Try to read as text first
                                content = item.read_text()
                                (target_dir / item.name).write_text(content)
                            except UnicodeDecodeError:
                                # If it fails, read as binary
                                content = item.read_bytes()
                                (target_dir / item.name).write_bytes(content)
                        elif item.is_dir():
                            copy_resource_dir(item, target_dir / item.name)
                
                streamlit_dir = temp_dir / "streamlit_app"
                copy_resource_dir(streamlit_resources, streamlit_dir)
                app_file = streamlit_dir / "app.py"
                
        except Exception as e:
            # Fall back to looking for local development copy
            possible_paths = [
                current_dir / "streamlit_app" / "app.py",
                current_dir.parent / "streamlit_app" / "app.py",
                Path(__file__).parent.parent.parent / "streamlit_app" / "app.py",
            ]
            
            for path in possible_paths:
                if path.exists():
                    app_file = path
                    break
        
        if not app_file or not app_file.exists():
            click.echo("❌ Could not find Streamlit app file.")
            click.echo("Please ensure the streamlit_app directory is available.")
            sys.exit(1)
        
        # Start Streamlit
        click.echo(f"🚀 Starting Podcast Creator Studio...")
        click.echo(f"   URL: http://{host}:{port}")
        click.echo(f"   Working directory: {current_dir}")
        click.echo(f"   App file: {app_file}")
        click.echo("\n   Press Ctrl+C to stop the server\n")
        
        # Change working directory to ensure relative paths work correctly
        os.chdir(current_dir)
        
        # Run streamlit
        cmd = [
            sys.executable, "-m", "streamlit", "run", 
            str(app_file),
            "--server.port", str(port),
            "--server.address", host,
            "--server.headless", "true",
            "--browser.gatherUsageStats", "false"
        ]
        
        subprocess.run(cmd)
        
    except KeyboardInterrupt:
        click.echo("\n👋 Shutting down Podcast Creator Studio...")
    except Exception as e:
        click.echo(f"❌ Error starting UI: {e}")
        sys.exit(1)


if __name__ == "__main__":
    cli()