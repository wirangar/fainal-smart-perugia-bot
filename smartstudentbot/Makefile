# Makefile for SmartStudentBot

.PHONY: help setup test lint run generate-handler run-dev test-fast test-unit test-all

help:
	@echo "Safe Development Commands:"
	@echo "  run-dev            : Run server in dev mode (no network calls, auto-reload)"
	@echo "  test-fast          : Run fast tests (unit & integration)"
	@echo "  test-unit          : Run only unit tests (no I/O)"
	@echo ""
	@echo "Other Commands:"
	@echo "  setup              : Install dependencies for development"
	@echo "  test-all           : Run all tests, including slow e2e tests"
	@echo "  lint               : Run ruff linter"
	@echo "  run                : (DEPRECATED) Use run-dev instead"
	@echo "  generate-handler   : Generate a new handler file"

# --- Safe Development Commands ---

run-dev:
	DEV_MODE=1 DISABLE_EXTERNAL_CALLS=1 STARTUP_SET_WEBHOOK=0 \
	uvicorn main:app --host 0.0.0.0 --port 8000 --reload

test-fast:
	pytest -m "unit or integration" -q -n auto

test-unit:
	pytest -m "unit" -q -n auto

# --- Other Commands ---

setup:
	pip install -r requirements.txt -r dev-requirements.txt

test-all:
	@echo "WARNING: This will run e2e tests which may hit live services."
	pytest -m "unit or integration or e2e" -q

lint:
	ruff check .

run:
	@echo "This command is deprecated. Use 'make run-dev' for safe local development."
	make run-dev

generate-handler:
	@read -p "Enter handler name (e.g., new_feature): " name; \
	python -m utils.cli generate-handler --name $$name
