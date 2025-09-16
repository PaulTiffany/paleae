# Contributing to Paleae

Thank you for your interest in contributing to Paleae! This project aims to make repository snapshots for AI analysis as simple and reliable as possible.

## Quick Start

1. **Fork and clone** the repository
2. **Install dev dependencies**: `pip install -e .[dev]`  
3. **Run tests**: `pytest` (should achieve 100% coverage)
4. **Check code quality**: `ruff check . && mypy . && pydocstyle paleae.py`

## Development Philosophy

Paleae follows these core principles:

- **Single file, zero runtime dependencies** - Keep `paleae.py` self-contained
- **Local-first** - No network calls, no external services
- **Predictable behavior** - Deterministic output, clear error messages
- **Comprehensive testing** - Property-based tests with Hypothesis, 100% coverage

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
- Follow the existing code style (enforced by ruff)
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
```

## Testing Guidelines

- **Unit tests**: Test individual functions with clear inputs/outputs
- **Property-based tests**: Use Hypothesis for edge cases and invariants
- **Integration tests**: Test complete workflows with temporary directories
- **Coverage requirement**: 100% line and branch coverage

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

- **Line length**: 100 characters (configured in `.ruff.toml`)
- **Type hints**: Required for all function signatures
- **Docstrings**: Required for public functions (checked by pydocstyle)
- **Error handling**: Use specific exceptions, avoid bare `except:`

## Making Changes

1. **Create a feature branch**: `git checkout -b feature/your-feature-name`
2. **Write tests first** (TDD approach preferred)
3. **Implement the change** while maintaining coverage
4. **Update documentation** if user-facing behavior changes
5. **Run the full test suite** before submitting

## Pull Request Process

1. **Run all checks locally**:
   ```bash
   pytest --cov=paleae --cov-branch
   ruff check .
   mypy .
   pydocstyle paleae.py
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

By contributing, you agree that your contributions will be licensed under the same MIT license that covers the project.