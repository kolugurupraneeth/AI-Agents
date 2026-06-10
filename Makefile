.PHONY: help install install-dev test lint format clean build docs

help:
	@echo "AI-Agents Development Commands"
	@echo "==============================="
	@echo "make install          - Install dependencies"
	@echo "make install-dev      - Install development dependencies"
	@echo "make test             - Run tests"
	@echo "make test-cov         - Run tests with coverage report"
	@echo "make lint             - Run linting checks"
	@echo "make format           - Format code with black and isort"
	@echo "make type-check       - Run type checking with mypy"
	@echo "make clean            - Clean up generated files"
	@echo "make build            - Build the project"
	@echo "make docs             - Generate documentation"

install:
	pip install -r requirements.txt

install-dev:
	pip install -r requirements-dev.txt

test:
	pytest tests/ -v

test-cov:
	pytest tests/ -v --cov=agents --cov-report=html --cov-report=term-missing

lint:
	flake8 . --max-line-length=100
	pylint agents/ --disable=C0111,C0103

format:
	black .
	isort .

type-check:
	mypy agents/ --ignore-missing-imports

clean:
	find . -type f -name '*.pyc' -delete
	find . -type d -name '__pycache__' -exec rm -rf {} +
	find . -type d -name '.pytest_cache' -exec rm -rf {} +
	find . -type d -name '.mypy_cache' -exec rm -rf {} +
	find . -type d -name '.coverage' -exec rm -rf {} +
	find . -type d -name 'htmlcov' -exec rm -rf {} +
	find . -type d -name '*.egg-info' -exec rm -rf {} +
	find . -type d -name 'build' -exec rm -rf {} +
	find . -type d -name 'dist' -exec rm -rf {} +

build: clean
	python -m build

docs:
	cd docs && make html

run-example:
	python examples/basic_usage.py

.DEFAULT_GOAL := help

