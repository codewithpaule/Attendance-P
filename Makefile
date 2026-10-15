.PHONY: run test lint format install clean db-migrate db-shell help

help:
	@echo "Available commands:"
	@echo "  make install       - Install dependencies"
	@echo "  make run           - Run development server"
	@echo "  make test          - Run tests"
	@echo "  make lint          - Run linters (ruff, mypy)"
	@echo "  make format        - Format code"
	@echo "  make db-migrate    - Run database migrations"
	@echo "  make db-shell      - Open database shell"
	@echo "  make clean         - Clean up generated files"

install:
	pip install -e .[dev]

run:
	python manage.py runserver

test:
	pytest

lint:
	ruff check .
	mypy .

format:
	ruff format .

db-migrate:
	python manage.py migrate

db-shell:
	python manage.py dbshell

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .mypy_cache .ruff_cache .pytest_cache htmlcov
