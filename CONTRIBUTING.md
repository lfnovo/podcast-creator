# Contributing to Podcast Creator

First off, thank you for considering contributing to Podcast Creator! 🎉 It's people like you that make this project better for everyone.

## 🎯 Ways to Contribute

There are many ways to contribute to this project:

- **🐛 Report bugs** and help us verify fixes as they are checked in
- **💡 Suggest new features** or enhancements
- **📝 Improve documentation** - fix typos, clarify usage, add examples
- **🔧 Submit bug fixes** - review our [open issues](https://github.com/lfnovo/podcast-creator/issues)
- **✨ Add new features** - check our roadmap or propose your own ideas
- **🎨 Improve UI/UX** - enhance the Streamlit interface
- **🧪 Add tests** - increase code coverage and reliability
- **🌍 Add translations** - help make the project accessible globally

## 🚀 Getting Started

### Prerequisites

- Python 3.10.6 or higher
- [uv](https://github.com/astral-sh/uv) (recommended) or pip
- Git

### Development Setup

1. **Fork the repository**
   ```bash
   # Click the 'Fork' button on GitHub, then clone your fork
   git clone https://github.com/YOUR-USERNAME/podcast-creator.git
   cd podcast-creator
   ```

2. **Create a virtual environment and install dependencies**
   ```bash
   # Using uv (recommended)
   uv sync
   
   # Or using pip
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -e ".[dev,ui]"
   ```

3. **Set up your environment**
   ```bash
   cp .env.example .env
   # Edit .env and add your API keys
   ```

4. **Run tests to ensure everything is working**
   ```bash
   uv run pytest -v
   # or
   make test
   ```

## 💻 Development Workflow

1. **Create a new branch for your feature/fix**
   ```bash
   git checkout -b feature/amazing-new-feature
   # or
   git checkout -b fix/issue-123
   ```

2. **Make your changes**
   - Write clear, self-documenting code
   - Follow the existing code style
   - Add docstrings to new functions/classes
   - Update tests as needed

3. **Test your changes**
   ```bash
   # Run tests
   uv run pytest -v
   
   # Run linting
   make lint
   make ruff
   
   # Test the CLI
   uv run podcast-creator --help
   
   # Test the UI (if applicable)
   uv run podcast-creator ui
   ```

4. **Commit your changes**
   ```bash
   git add .
   git commit -m "feat: add amazing new feature
   
   - Detailed description of what changed
   - Why this change was needed
   - Any breaking changes or migration notes"
   ```

## 📋 Pull Request Process

1. **Update documentation** if you've changed APIs or added features
2. **Add tests** for new functionality
3. **Ensure all tests pass** - we have CI that will check this
4. **Update the README.md** if needed
5. **Submit your pull request**:
   - Use a clear, descriptive title
   - Fill out the PR template completely
   - Link any related issues
   - Add screenshots for UI changes

### PR Title Convention

We follow conventional commits for PR titles:

- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation only changes
- `style:` - Code style changes (formatting, etc)
- `refactor:` - Code changes that neither fix bugs nor add features
- `perf:` - Performance improvements
- `test:` - Adding or updating tests
- `chore:` - Maintenance tasks

Examples:
- `feat: add support for Anthropic Claude models`
- `fix: resolve audio synchronization issue in long podcasts`
- `docs: improve episode profile documentation`

## 🧪 Testing Guidelines

- Write tests for new features using pytest
- Maintain or improve code coverage
- Test edge cases and error conditions
- Use meaningful test names that describe what's being tested

Example test structure:
```python
def test_create_podcast_with_episode_profile():
    """Test that create_podcast works correctly with episode profiles."""
    # Arrange
    content = "Test content"
    
    # Act
    result = await create_podcast(
        content=content,
        episode_profile="tech_discussion"
    )
    
    # Assert
    assert result is not None
    assert "final_output_file_path" in result
```

## 🎨 Code Style

- We use `ruff` for code formatting and linting
- Follow PEP 8 guidelines
- Use type hints where possible
- Write descriptive variable and function names
- Keep functions focused and small
- Add docstrings to all public functions/classes

Example:
```python
async def generate_podcast_outline(
    content: str,
    briefing: str,
    num_segments: int = 4
) -> Outline:
    """Generate a structured outline for a podcast episode.
    
    Args:
        content: The source content to base the podcast on
        briefing: Instructions for how to approach the content
        num_segments: Number of segments to create
        
    Returns:
        Outline object containing structured segments
        
    Raises:
        ValueError: If content is empty or num_segments < 1
    """
    # Implementation here
```

## 📚 Documentation

- Update docstrings for any changed functions
- Add examples for new features
- Update the README if you add new functionality
- Consider adding Jupyter notebook examples for complex features
- Keep documentation clear and concise

## 🐛 Reporting Bugs

Before submitting a bug report:

1. **Check existing issues** to avoid duplicates
2. **Try the latest version** - your issue might be fixed
3. **Collect information**:
   - Python version
   - Operating system
   - Full error messages and stack traces
   - Steps to reproduce
   - Expected vs actual behavior

## 💡 Suggesting Features

We love feature suggestions! Please:

1. **Check existing issues and discussions**
2. **Provide context** - what problem does this solve?
3. **Be specific** about the proposed solution
4. **Consider the scope** - does it fit the project's goals?

## 🤝 Community Guidelines

- Be respectful and constructive
- Welcome newcomers and help them get started
- Focus on what is best for the community
- Show empathy towards other community members
- Gracefully accept constructive criticism

## 🔍 Where to Find Tasks

- [Good First Issues](https://github.com/lfnovo/podcast-creator/labels/good%20first%20issue) - perfect for newcomers
- [Help Wanted](https://github.com/lfnovo/podcast-creator/labels/help%20wanted) - issues where we need help
- [Feature Requests](https://github.com/lfnovo/podcast-creator/labels/enhancement) - new features to implement

## 📮 Getting Help

If you need help:

1. Check the [README](README.md) and documentation
2. Look through [existing issues](https://github.com/lfnovo/podcast-creator/issues)
3. Ask in the issue comments
4. Be patient - maintainers have other responsibilities too

## 🙏 Recognition

Contributors will be:
- Listed in our [Contributors](#) section
- Mentioned in release notes for significant contributions
- Given credit in relevant documentation

## 📄 License

By contributing, you agree that your contributions will be licensed under the same MIT License that covers this project.

---

Thank you for contributing to Podcast Creator! Your efforts help make AI-powered podcast creation accessible to everyone. 🚀