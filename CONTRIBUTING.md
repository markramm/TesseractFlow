# Contributing to TesseractFlow

Thank you for your interest in contributing to TesseractFlow! This document provides guidelines and information for contributors.

## Getting Started

### Development Setup

1. **Clone the repository:**
```bash
git clone https://github.com/markramm/TesseractFlow.git
cd TesseractFlow
```

2. **Create a virtual environment:**
```bash
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install development dependencies:**
```bash
pip install -e ".[dev]"
```

4. **Install pre-commit hooks:**
```bash
pre-commit install
```

## Development Workflow

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov

# Run specific test file
pytest tests/test_taguchi.py

# Run with verbose output
pytest -v
```

### Code Quality

We use several tools to maintain code quality:

**Black (formatting):**
```bash
black tesseract_flow/ tests/
```

**Ruff (linting):**
```bash
ruff check tesseract_flow/ tests/
ruff check --fix tesseract_flow/ tests/  # Auto-fix issues
```

**MyPy (type checking):**
```bash
mypy tesseract_flow/
```

**Pre-commit (all checks):**
```bash
pre-commit run --all-files
```

### Commit Messages

We follow [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation changes
- `test:` Test changes
- `refactor:` Code refactoring
- `chore:` Maintenance tasks

**Examples:**
```
feat: Add pairwise A/B evaluator
fix: Correct L16 array generation
docs: Update README with new examples
test: Add integration test for Taguchi L8
```

## Contributing Guidelines

### Reporting Issues

When reporting bugs, please include:
- Python version
- TesseractFlow version
- Minimal reproducible example
- Error message/stack trace
- Expected vs actual behavior

### Feature Requests

When proposing features:
- Describe the use case
- Explain why existing features don't solve the problem
- Provide examples of how the API would look
- Consider implementation complexity

### Pull Requests

1. **Fork and create a branch:**
```bash
git checkout -b feat/my-new-feature
```

2. **Make your changes:**
- Write tests for new functionality
- Update documentation as needed
- Ensure all tests pass
- Run code quality tools

3. **Commit and push:**
```bash
git add .
git commit -m "feat: Add my new feature"
git push origin feat/my-new-feature
```

4. **Create pull request:**
- Describe the changes
- Link related issues
- Provide context for reviewers

### Code Style

- Follow PEP 8 (enforced by Black and Ruff)
- Use type hints for all function signatures
- Write docstrings for public APIs (Google style)
- Keep functions focused and small
- Prefer composition over inheritance

**Example:**
```python
from typing import List, Optional

def compute_main_effects(
    results: List[float],
    array: np.ndarray,
    variable_names: List[str]
) -> Dict[str, Dict[str, float]]:
    """
    Compute main effects for each variable.

    Args:
        results: Utility scores for each test
        array: Taguchi orthogonal array
        variable_names: Names of variables

    Returns:
        Main effects analysis with contribution percentages

    Example:
        >>> effects = compute_main_effects([0.7, 0.8], array, ["temp", "model"])
        >>> effects["temp"]["contribution_pct"]
        35.2
    """
    # Implementation
```

### Testing Guidelines

- Write unit tests for core logic
- Write integration tests for workflows
- Use fixtures for common test data
- Mock external API calls
- Aim for >80% code coverage

**Example:**
```python
import pytest
from tesseract_flow import TaguchiExperiment, ExperimentVariable

def test_l8_generates_8_configs():
    """Test that L8 array generates 8 test configurations."""
    variables = {
        "temp": ExperimentVariable(name="temp", level_1=0.3, level_2=0.7),
        "model": ExperimentVariable(name="model", level_1="gpt-4", level_2="claude"),
    }

    experiment = TaguchiExperiment(variables, design_type="taguchi_l8")

    assert len(experiment.test_configs) == 8
    assert all("temp" in config for config in experiment.test_configs)
```

## Project Structure

```
TesseractFlow/
├── tesseract_flow/          # Main package
│   ├── core/                # Core workflow components
│   │   ├── base_workflow.py
│   │   ├── config.py
│   │   └── strategies.py
│   ├── experiments/         # Taguchi DOE
│   │   └── taguchi.py
│   ├── evaluation/          # Quality evaluation
│   │   ├── evaluators.py
│   │   └── optimization.py
│   └── cli.py              # Command-line interface
├── tests/                   # Test suite
├── docs/                    # Documentation
├── examples/                # Example workflows
└── pyproject.toml          # Package configuration
```

## Areas for Contribution

### High Priority

- **L16/L18 orthogonal arrays** - Extend beyond L8
- **Pairwise A/B evaluator** - More robust evaluation
- **Judge ensembles** - Multiple LLM judges
- **Web UI** - Dashboard for experiments and approvals
- **Example workflows** - More real-world examples

### Medium Priority

- **Provider integrations** - Azure, AWS Bedrock, etc.
- **TruLens integration** - Wrap their evaluators
- **Confirmation experiments** - Validate optimal configs
- **Advanced visualizations** - Interactive Pareto plots

### Good First Issues

- **Documentation improvements** - Tutorials, guides
- **Example workflows** - Domain-specific examples
- **Test coverage** - Increase test coverage
- **Type hints** - Add missing type annotations
- **Error messages** - Improve error messages

## Release Process

1. Update version in `pyproject.toml` and `__init__.py`
2. Update `CHANGELOG.md`
3. Create release on GitHub
4. Build and publish to PyPI:
```bash
python -m build
twine upload dist/*
```

## Community

- **GitHub Discussions** - Ask questions, share ideas
- **GitHub Issues** - Bug reports, feature requests
- **Discord** - Coming soon

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

## Questions?

If you have questions about contributing, please:
1. Check existing documentation
2. Search GitHub issues
3. Open a new issue with the "question" label

Thank you for contributing to TesseractFlow!
