# Contributing to large-scale-refactor

Thanks for your interest in contributing to the `large-scale-refactor` skill.

## Getting Started

1. Fork the repository
2. Clone your fork and create a feature branch
3. Make your changes
4. Run the test suite (see below)
5. Submit a pull request

## Running Tests

The skill's verification scripts have a pytest test suite. No external dependencies
are required beyond Python 3.8+ and pytest.

```bash
# Install pytest (if not already available)
pip install pytest

# Run the test suite
python -m pytest large-scale-refactor/scripts/test_verify_scope.py -v
```

## What to Contribute

- Bug fixes in the verification scripts (`verify_scope.py`, `generate_allowlist.py`)
- New test cases for edge cases in pattern matching
- Improvements to templates (`templates/`)
- Platform-specific notes for additional AI coding agents
- Documentation clarifications

## PR Conventions

- One logical change per PR
- Include a test case if your change affects `verify_scope.py` or `generate_allowlist.py`
- Update `SKILL.md` if your change affects guardrail language or protocols
- Keep commit messages descriptive: `fix(verify_scope): handle edge case in directory prefix matching`

## Code Style

- Python scripts use stdlib only (no external dependencies)
- Follow existing patterns in the codebase
- Type hints are encouraged but not strictly required

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
