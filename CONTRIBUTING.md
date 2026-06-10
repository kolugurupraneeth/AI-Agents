# Contributing to AI-Agents

Thank you for your interest in contributing to AI-Agents! We welcome contributions from the community. This document provides guidelines and instructions for contributing.

## Getting Started

1. Fork the repository on GitHub
2. Clone your fork locally
3. Create a new branch for your feature or bugfix:
   ```bash
   git checkout -b feature/your-feature-name
   ```

## Setting Up Your Development Environment

```bash
# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install development dependencies
pip install -r requirements-dev.txt
```

## Making Changes

### Code Style

- We use **Black** for code formatting
- We use **isort** for import sorting
- Follow PEP 8 style guidelines
- Write descriptive commit messages

### Before Submitting

```bash
# Format your code
black .
isort .

# Run linting
flake8 .

# Type checking
mypy agents/

# Run tests
pytest

# Check test coverage
pytest --cov=agents
```

## Testing

- Write tests for new features
- Ensure all tests pass before submitting a PR
- Aim for >80% code coverage

Example test:
```python
def test_agent_creation():
    agent = Agent(name="TestAgent")
    assert agent.name == "TestAgent"
```

## Commit Messages

Use clear, descriptive commit messages:
```
feat: Add agent memory module
fix: Resolve issue with async execution
docs: Update API documentation
test: Add tests for orchestration
```

## Submitting a Pull Request

1. Push your changes to your fork
2. Create a Pull Request on GitHub
3. Provide a clear description of your changes
4. Reference any related issues
5. Ensure CI/CD checks pass

## Reporting Issues

When reporting issues:
- Use a clear, descriptive title
- Describe the expected behavior
- Include steps to reproduce
- Provide code snippets if applicable
- Mention your Python version and OS

## Questions?

Feel free to open an issue or reach out to the maintainers.

---

Thank you for contributing! 🚀

