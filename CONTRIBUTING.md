# Contributing to Music Advisor

Thank you for your interest in contributing to Music Advisor! This guide will help you get started with setting up your development environment and understanding our workflow.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Environment Setup](#development-environment-setup)
- [Making Changes](#making-changes)
- [Testing Guidelines](#testing-guidelines)
- [Submitting Contributions](#submitting-contributions)
- [Coding Standards](#coding-standards)
- [What We're Looking For](#what-were-looking-for)

## Code of Conduct

By participating in this project, you agree to abide by our [Code of Conduct](CODE_OF_CONDUCT.md). Please read it before contributing.

## Getting Started

### Prerequisites

- Python 3.11+ (3.9+ supported, 3.11+ recommended)
- Git
- ~5-10 GB disk space for data/bootstrap
- macOS or Linux (Windows via WSL2)
- Optional: ffmpeg, libsamplerate, fftw (for audio sidecars)

### First Steps

1. **Fork the Repository**: Click the "Fork" button on GitHub to create your own copy
2. **Clone Your Fork**:
   ```bash
   git clone https://github.com/YOUR_USERNAME/music-advisor.git
   cd music-advisor
   ```
3. **Add Upstream Remote**:
   ```bash
   git remote add upstream https://github.com/keithhetrick/music-advisor.git
   ```

## Development Environment Setup

### Complete Setup (Recommended)

```bash
# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Bootstrap everything (venv + deps + data + smoke tests)
make bootstrap-locked

# Verify setup
make quick-check
```

### Manual Setup (Alternative)

```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements.lock || true

# Bootstrap data (optional, requires network access)
python infra/scripts/data_bootstrap.py --manifest infra/scripts/data_manifest.json

# Install audio sidecar dependencies (macOS)
brew install ffmpeg libsamplerate fftw
pip install essentia
```

### Sparse Checkout (For Targeted Work)

If you're working on a specific component, use sparse checkout to reduce repository size:

```bash
git sparse-checkout init --cone
git sparse-checkout set hosts/advisor_host tools shared engines/audio_engine docs

# Install only what you need
pip install -e shared -e hosts/advisor_host
```

### Using the Helper CLI

The `ma_helper` CLI streamlines many development tasks:

```bash
# Set up alias (recommended)
alias ma="python -m ma_helper"

# Quick orientation
ma quickstart

# Run tests for specific project
ma test <project_name>

# Run only affected tests
ma affected --base origin/main

# Start development dashboard
ma chat-dev  # Uses tmux if available
```

## Making Changes

### Branch Strategy

1. **Create a Feature Branch**:
   ```bash
   git checkout -b feature/your-feature-name
   # or
   git checkout -b fix/your-bug-fix
   ```

2. **Keep Your Branch Updated**:
   ```bash
   git fetch upstream
   git rebase upstream/main
   ```

### Commit Guidelines

- Write clear, descriptive commit messages
- Use present tense ("Add feature" not "Added feature")
- Reference issues when applicable: `Fix #123: Description of fix`
- Keep commits focused on a single change
- Example format:
  ```
  area: Brief description (50 chars or less)
  
  More detailed explanation if needed (wrap at 72 chars).
  Include motivation for change and contrast with previous behavior.
  
  Fixes #issue_number
  ```

### Areas/Components

Use these prefixes for commit messages:
- `audio_engine:` - Audio extraction and processing
- `host:` - Chat host and API
- `tools:` - CLI tools and utilities
- `docs:` - Documentation updates
- `infra:` - Infrastructure and build scripts
- `engines:` - Recommendation, TTC, or lyrics engines
- `shared:` - Shared utilities and configuration
- `tests:` - Test additions or fixes

## Testing Guidelines

### Running Tests

```bash
# Run all tests
make quick-check

# Run tests for affected code only
infra/scripts/test_affected.sh

# Run specific project tests
python tools/ma_orchestrator.py test <project_name>

# Run with helper CLI
ma test <project_name>
```

### Writing Tests

- Add tests alongside code changes
- Use existing fixtures in `tests/fixtures` when possible
- Follow existing test patterns and conventions
- Ensure tests are isolated and reproducible
- Test both success and failure cases

### Test Structure

```python
def test_feature_name():
    """Test description explaining what is being tested."""
    # Arrange: Set up test conditions
    
    # Act: Execute the code being tested
    
    # Assert: Verify expected outcomes
```

## Submitting Contributions

### Before Submitting

1. **Run Tests**: Ensure all tests pass
   ```bash
   make quick-check
   ```

2. **Run Linters** (if touching host code):
   ```bash
   make lint
   make typecheck
   ```

3. **Update Documentation**: 
   - Update relevant docs if you changed behavior
   - Keep README/doc links valid
   - Add examples for new features

4. **Security Check**:
   - No secrets, tokens, or presigned URLs in code
   - No raw audio or databases committed
   - Follow secure coding practices

### Creating a Pull Request

1. **Push Your Changes**:
   ```bash
   git push origin your-branch-name
   ```

2. **Open a PR**: Go to GitHub and click "New Pull Request"

3. **Fill Out the Template**: Our PR template will guide you through:
   - Summary of changes
   - Testing performed
   - Documentation updates
   - Security considerations

4. **Link Issues**: Reference related issues in your PR description

### PR Review Process

- A maintainer will review your PR
- Address any feedback or requested changes
- Once approved, your PR will be merged
- Thank you for your contribution! 🎉

## Coding Standards

### Python Code Style

- Follow PEP 8 conventions
- Use existing code formatting (black-style preferred)
- Avoid trailing whitespace
- Keep imports organized:
  ```python
  # Standard library
  import os
  
  # Third-party
  import numpy as np
  
  # Local/project
  from engines.audio_engine import extract
  ```

### Best Practices

- **Imports**: Keep imports relative to project namespaces (`engines/*`, `hosts/*`, `shared/*`)
- **Path Handling**: Use path helpers (MA_DATA_ROOT via `shared.config.paths`) instead of hardcoded paths
- **Error Handling**: Provide clear error messages with context
- **Logging**: Use appropriate logging levels; support LOG_SANDBOX and LOG_REDACT
- **Documentation**: Add docstrings to public functions and classes
- **Type Hints**: Use type hints for function signatures when possible

### Things to Avoid

- ❌ Large reformat-only PRs
- ❌ sys.path hacks or modifying Python path
- ❌ Committing raw audio, databases, or large files
- ❌ Hardcoded paths (use environment variables and path helpers)
- ❌ Secrets or tokens in code or manifests
- ❌ Breaking changes without discussion

## What We're Looking For

We welcome various types of contributions:

### 🐛 Bug Fixes
- Fix reported issues
- Improve error handling
- Resolve edge cases

### ✨ New Features
- Audio analysis improvements
- New CLI commands
- Integration with additional tools
- UI/UX enhancements

### 📖 Documentation
- Improve existing docs
- Add examples and tutorials
- Fix typos and clarity issues
- Create guides for common workflows

### 🧪 Tests
- Increase test coverage
- Add integration tests
- Test edge cases and error conditions

### 🎨 Design & UI
- macOS app improvements
- Design system (MAStyle) enhancements
- UI wireframes and mockups

### 🔌 Integrations
- DAW plugins (C++/JUCE)
- New audio backend support
- External service integrations

## Reporting Issues

### Bug Reports

Use our [bug report template](.github/ISSUE_TEMPLATE/bug_report.md) and include:

- Clear description of the issue
- Steps to reproduce
- Expected vs actual behavior
- Environment details (OS, Python version, commands run)
- Relevant logs (redact sensitive data)
- MA_DATA_ROOT override status

### Feature Requests

Use our [feature request template](.github/ISSUE_TEMPLATE/feature_request.md) and describe:

- The problem or use case
- Proposed solution
- Alternatives considered
- Impact area (audio engine, host, shared, docs, etc.)

### Questions and Support

For questions and support, please:
- Check existing documentation in `docs/`
- Search existing issues
- See [SUPPORT.md](SUPPORT.md) for additional resources
- Create a discussion thread (not an issue) for general questions

## Release Process

Releases are managed by maintainers. If you're interested in the process:

1. `make clean` - Clean build artifacts
2. `make quick-check` - Run full test suite
3. Update `CHANGELOG.md` with changes
4. Follow versioning per `RELEASE.md`
5. Tag release and publish

## Getting Help

- **Documentation**: Comprehensive docs in `docs/` directory
- **Helper CLI**: Run `ma help` or `python -m ma_helper help`
- **Issues**: Search or create GitHub issues
- **Code Review**: Ask questions in your PR
- **Community**: Be respectful and collaborative

## Additional Resources

- [README.md](README.md) - Project overview and quick start
- [docs/](docs/) - Detailed documentation
- [SECURITY.md](SECURITY.md) - Security policies
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Common issues
- [docs/ops/commands.md](docs/ops/commands.md) - Command reference
- [docs/architecture/README.md](docs/architecture/README.md) - Architecture overview

---

Thank you for contributing to Music Advisor! Your efforts help make this tool better for everyone. 🎵
