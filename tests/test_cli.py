"""Tests for CLI commands."""

import tempfile
from pathlib import Path

from click.testing import CliRunner

from podcast_creator.cli import cli


class TestInitCommand:
    """Test cases for the init CLI command."""
    
    def test_init_fresh_directory(self):
        """Test init in a fresh directory creates all files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            runner = CliRunner()
            result = runner.invoke(cli, ['init', '--output-dir', temp_dir])
            
            assert result.exit_code == 0
            assert "🎙️ Initializing podcast creator" in result.output
            assert "🎉 Initialization complete!" in result.output
            assert "Files copied: 5" in result.output
            
            # Check that all files were created
            temp_path = Path(temp_dir)
            assert (temp_path / "prompts" / "podcast" / "outline.jinja").exists()
            assert (temp_path / "prompts" / "podcast" / "transcript.jinja").exists()
            assert (temp_path / "speakers_config.json").exists()
            assert (temp_path / "episodes_config.json").exists()
            assert (temp_path / "example_usage.py").exists()
    
    def test_init_with_force_flag(self):
        """Test init with --force flag overwrites existing files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            runner = CliRunner()
            temp_path = Path(temp_dir)
            
            # Create an existing file
            existing_file = temp_path / "speakers_config.json"
            existing_file.parent.mkdir(parents=True, exist_ok=True)
            existing_file.write_text("existing content")
            
            result = runner.invoke(cli, ['init', '--output-dir', temp_dir, '--force'])
            
            assert result.exit_code == 0
            assert "⚠ Overwriting existing speaker configuration" in result.output
            assert "Files copied: 5" in result.output
            
            # Check that file was overwritten
            assert existing_file.exists()
            assert "existing content" not in existing_file.read_text()
    
    def test_init_interactive_yes(self):
        """Test interactive prompt with 'yes' response."""
        with tempfile.TemporaryDirectory() as temp_dir:
            runner = CliRunner()
            temp_path = Path(temp_dir)
            
            # Create an existing file
            existing_file = temp_path / "speakers_config.json"
            existing_file.parent.mkdir(parents=True, exist_ok=True)
            existing_file.write_text("existing content")
            
            # Simulate user input: 'y' for yes
            result = runner.invoke(cli, ['init', '--output-dir', temp_dir], input='y\n')
            
            assert result.exit_code == 0
            assert "📄 File already exists:" in result.output
            assert "⚠ Overwriting existing speaker configuration" in result.output
            assert "Files copied: 5" in result.output
    
    def test_init_interactive_no(self):
        """Test interactive prompt with 'no' response."""
        with tempfile.TemporaryDirectory() as temp_dir:
            runner = CliRunner()
            temp_path = Path(temp_dir)
            
            # Create an existing file
            existing_file = temp_path / "speakers_config.json"
            existing_file.parent.mkdir(parents=True, exist_ok=True)
            existing_file.write_text("existing content")
            
            # Simulate user input: 'n' for no to all prompts
            result = runner.invoke(cli, ['init', '--output-dir', temp_dir], input='n\nn\nn\nn\nn\n')
            
            assert result.exit_code == 0
            assert "📄 File already exists:" in result.output
            assert "→ Skipped existing speaker configuration" in result.output
            assert "Files copied: 4" in result.output
            assert "Files skipped: 1" in result.output
            
            # Check that existing file was not modified
            assert existing_file.read_text() == "existing content"
    
    def test_init_interactive_all(self):
        """Test interactive prompt with 'all' response."""
        with tempfile.TemporaryDirectory() as temp_dir:
            runner = CliRunner()
            temp_path = Path(temp_dir)
            
            # Create multiple existing files
            (temp_path / "speakers_config.json").write_text("existing1")
            (temp_path / "episodes_config.json").write_text("existing2")
            
            # Simulate user input: 'a' for all (overwrite all)
            result = runner.invoke(cli, ['init', '--output-dir', temp_dir], input='a\n')
            
            assert result.exit_code == 0
            assert "📄 File already exists:" in result.output
            assert "⚠ Overwriting existing speaker configuration" in result.output
            assert "⚠ Overwriting existing episode configuration" in result.output
            assert "Files copied: 5" in result.output
    
    def test_init_interactive_skip_all(self):
        """Test interactive prompt with 'skip all' response."""
        with tempfile.TemporaryDirectory() as temp_dir:
            runner = CliRunner()
            temp_path = Path(temp_dir)
            
            # Create multiple existing files
            (temp_path / "speakers_config.json").write_text("existing1")
            (temp_path / "episodes_config.json").write_text("existing2")
            
            # Simulate user input: 's' for skip all
            result = runner.invoke(cli, ['init', '--output-dir', temp_dir], input='s\n')
            
            assert result.exit_code == 0
            assert "📄 File already exists:" in result.output
            assert "→ Skipped existing speaker configuration" in result.output
            assert "→ Skipped existing episode configuration" in result.output
            assert "Files copied: 3" in result.output
            assert "Files skipped: 2" in result.output
    
    def test_init_creates_directory_structure(self):
        """Test init creates proper directory structure."""
        with tempfile.TemporaryDirectory() as temp_dir:
            runner = CliRunner()
            target_dir = Path(temp_dir) / "my_project"
            
            result = runner.invoke(cli, ['init', '--output-dir', str(target_dir)])
            
            assert result.exit_code == 0
            assert "✓ Created output directory:" in result.output
            assert target_dir.exists()
            assert (target_dir / "prompts" / "podcast").exists()
    
    def test_init_help_text(self):
        """Test init command help text."""
        runner = CliRunner()
        result = runner.invoke(cli, ['init', '--help'])
        
        assert result.exit_code == 0
        assert "Initialize podcast creator templates and configuration" in result.output
        assert "--force" in result.output
        assert "Overwrite existing files without prompting" in result.output
        assert "--output-dir" in result.output


class TestVersionCommand:
    """Test cases for the version CLI command."""
    
    def test_version_command(self):
        """Test version command shows version information."""
        runner = CliRunner()
        result = runner.invoke(cli, ['version'])
        
        assert result.exit_code == 0
        assert "podcast-creator" in result.output