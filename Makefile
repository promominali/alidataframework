PYTHON ?= python
PIP ?= pip

.PHONY: help install-dev compose-up compose-down test-unit

help:
	@echo "aliframework Makefile"
	@echo "  install-dev   - install package in editable mode with dev extras"
	@echo "  compose-up    - start local services via docker-compose"
	@echo "  compose-down  - stop local services"
	@echo "  test-unit     - run unit tests (no external services)"
	@echo "  test-all      - run full test suite with coverage"
	@echo "  lint          - run ruff linting"
	@echo "  typecheck     - run mypy type checking"

install-dev:
	$(PIP) install -e .[dev]

compose-up:
	docker compose up -d

compose-down:
	docker compose down

test-unit:
	PYTHONPATH=. pytest tests/unit

# Full test suite including coverage (unit + integration)
# Integration tests require docker compose services to be running.
# See README for details.
test-all:
	PYTHONPATH=. pytest --cov=aliframework --cov-report=term-missing tests

lint:
	ruff check aliframework tests
	ruff format --check aliframework tests

typecheck:
	mypy aliframework
