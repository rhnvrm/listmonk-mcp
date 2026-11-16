.PHONY: check lint format test build docs

check: lint test

lint:
	uv run --frozen --extra dev ruff check src tests scripts
	uv run --frozen --extra dev ruff format --check src tests scripts
	uv run --frozen --extra dev mypy src

format:
	uv run --frozen --extra dev ruff check --fix src tests scripts
	uv run --frozen --extra dev ruff format src tests scripts

test:
	uv run --frozen --extra dev pytest

build:
	uv build
	uv run --frozen --extra dev twine check dist/*

docs:
	moat build docs/ _site/
