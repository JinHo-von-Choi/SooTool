.PHONY: test lint typecheck serve format
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
