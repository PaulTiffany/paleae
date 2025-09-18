# Contributing to Paleae

Thank you for your interest in contributing to Paleae! This project aims to make repository snapshots for AI analysis as simple and reliable as possible.

## Quick Start

1. **Fork and clone** the [repository](https://github.com/PaulTiffany/paleae)
2. **Install dev dependencies**: `pip install -e .[dev]` (see [`pyproject.toml`](./pyproject.toml) for details)
3. **Run tests**: `pytest` (should achieve 100% coverage, enforced by [`pytest-cov`](https://pytest-cov.readthedocs.io/))
4. **Check code quality**: `ruff check .` ([Ruff](https://docs.astral.sh/ruff/)), `mypy .` ([MyPy](https://mypy.readthedocs.io/)), `pydocstyle paleae.py` ([Pydocstyle](https://pydocstyle.readthedocs.io/))

## Development Philosophy

Paleae follows these core principles:

- **Single file, zero runtime dependencies** - Keep [`paleae.py`](./paleae.py) self-contained
- **Local-first** - No network calls, no external services
- **Predictable behavior** - Deterministic output, clear error messages
- **Comprehensive testing** - Property-based tests with [Hypothesis](https://hypothesis.readthedocs.io/), 100% coverage

## Types of Contributions

### Bug Reports
- Use GitHub Issues with clear reproduction steps
- Include your OS, Python version, and example repository structure
- Attach the problematic snapshot output if relevant

### Feature Requests
- Check existing issues first to avoid duplicates
- Explain the use case and why it benefits AI analysis workflows
- Consider if the feature aligns with the "lean but powerful" philosophy

### Code Contributions
- All changes require tests with full coverage maintained
- Follow the existing code style (enforced by [Ruff](https://docs.astral.sh/ruff/))
- Update documentation for user-facing changes

## Development Setup

```bash
# Clone your fork
git clone https://github.com/YOUR-USERNAME/paleae.git
cd paleae

# Install in development mode
pip install -e .[dev]

# Run the full test suite
pytest --cov=paleae --cov-branch --cov-report=term-missing

# Check code quality
ruff check .
mypy .
pydocstyle paleae.py
bandit -r paleae.py # Security scan with [Bandit](https://bandit.readthedocs.io/)
```

## Testing Guidelines

- **Unit tests**: Test individual functions with clear inputs/outputs
- **Property-based tests**: Use Hypothesis for edge cases and invariants
- **Integration tests**: Test complete workflows with temporary directories
- **Coverage requirement**: 100% line and branch coverage (enforced by [`pytest-cov`](https://pytest-cov.readthedocs.io/))

Example test pattern:
```python
def test_feature_basic_case():
    """Test the happy path."""
    # Arrange, Act, Assert

@given(st.text())
def test_feature_property(input_text):
    """Property-based test for edge cases."""
    # Test invariants that should always hold
```

## Code Style

- **Line length**: 100 characters (configured in [`./.ruff.toml`](./.ruff.toml))
- **Type hints**: Required for all function signatures (see [Python Typing](https://docs.python.org/3/library/typing.html))
- **Docstrings**: Required for public functions (checked by [Pydocstyle](https://pydocstyle.readthedocs.io/))
- **Error handling**: Use specific exceptions, avoid bare `except:`

## Making Changes

1. **Create a feature branch**: `git checkout -b feature/your-feature-name`
2. **Write tests first** (TDD approach preferred)
3. **Implement the change** while maintaining coverage
4. **Update documentation** if user-facing behavior changes
5. **Run the full test suite** before submitting

## Pull Request Process

1. **Run all checks locally**: The same checks run automatically on every pull request. You can view the full workflow definition [here](.github/workflows/ci.yml).
   ```bash
   pytest --cov=paleae --cov-branch
   ruff check .
   mypy .
   pydocstyle paleae.py
   bandit -r paleae.py # Security scan
   ```

2. **Update the version** in `paleae.py` and `pyproject.toml` if appropriate
3. **Write a clear PR description** explaining the change and motivation
4. **Link to related issues** using GitHub keywords (`fixes #123`)

## Release Process

Releases are handled by maintainers:
1. Version bump in `paleae.py` and `pyproject.toml`
2. Update changelog/release notes
3. Tag release and publish to PyPI
4. Update website if needed

## Questions?

- **General discussion**: GitHub Discussions
- **Bug reports**: GitHub Issues  
- **Quick questions**: Open an issue with the "question" label

## License

By contributing, you agree that your contributions will be licensed under the same [MIT license](./LICENSE) that covers the project.
