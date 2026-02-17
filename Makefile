.PHONY: help dev install lint typecheck test format clean docker-up docker-down seed

help:
	@echo "Available commands:"
	@echo "  make dev         - Run development server"
	@echo "  make install     - Install dependencies"
	@echo "  make lint        - Run linters"
	@echo "  make typecheck   - Run type checking"
	@echo "  make test        - Run tests"
	@echo "  make format      - Format code"
	@echo "  make clean       - Clean cache files"
	@echo "  make docker-up   - Start docker services"
	@echo "  make docker-down - Stop docker services"
	@echo "  make seed        - Seed database with sample data"

install:
	cd backend && pip install -e .[dev]

dev:
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

lint:
	cd backend && ruff check app/

typecheck:
	cd backend && mypy app/

test:
	cd backend && pytest app/tests/ -v

format:
	cd backend && ruff format app/

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

seed:
	cd backend && python -m app.scripts.seed_db
