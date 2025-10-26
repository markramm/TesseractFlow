# Development Environment Setup

This guide explains how to get a local development environment ready for working on TesseractFlow.

## Prerequisites

- Python 3.11 or newer
- Poetry or pip for dependency management
- Git
- Make (optional but recommended)

## Installation Steps

1. **Clone the repository**
   ```bash
   git clone https://github.com/markramm/TesseractFlow.git
   cd TesseractFlow
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows use `.venv\\Scripts\\activate`
   ```

3. **Install dependencies**
   ```bash
   pip install --upgrade pip
   pip install -e .[dev]
   ```

4. **Set environment variables**
   ```bash
   cp .env.example .env
   # Update provider API keys as needed
   ```

5. **Run tests to verify setup**
   ```bash
   pytest
   ```

## Tooling

- **Formatting**: `black` (configured via `pyproject.toml`)
- **Linting**: `ruff`
- **Type checking**: `mypy`
- **Testing**: `pytest` with coverage reporting

Use `pre-commit install` to enable automated checks before each commit.

## Troubleshooting

If dependencies fail to install, ensure you are using Python 3.11+ and upgrade `pip`.
For issues with native extensions, install system build tools (e.g., `build-essential` on Ubuntu).
