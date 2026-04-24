.PHONY: test lint typecheck serve format release-preflight draft-changelog
test:
	uv run pytest -v --cov=sootool --cov-report=term-missing
lint:
	uv run ruff check src tests
format:
	uv run ruff format src tests
typecheck:
	uv run mypy src/sootool
serve:
	uv run python -m sootool
release-preflight:
	uv run python scripts/release_preflight.py
draft-changelog:
	uv run python scripts/draft_changelog.py
