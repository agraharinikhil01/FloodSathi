.PHONY: help setup dev seed test lint test-backend test-frontend

PYTHON ?= C:/Python314/python.exe
NPM ?= npm

help:
	@echo "FloodSaathi Development Commands:"
	@echo "  make setup    - Install dependencies for backend and frontend"
	@echo "  make seed     - Initialise and seed the SQLite database"
	@echo "  make dev      - Run backend (:8000) and frontend (:5173)"
	@echo "  make test     - Run all backend and frontend tests"
	@echo "  make lint     - Run code quality linters (ruff, tsc)"

setup:
	$(PYTHON) -m pip install -r requirements.txt
	cd frontend && $(NPM) install

seed:
	$(PYTHON) -m backend.app.seed.seed_data

dev-backend:
	$(PYTHON) -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload

dev-frontend:
	cd frontend && $(NPM) run dev

test-backend:
	$(PYTHON) -m pytest backend/tests/ -v

test-frontend:
	cd frontend && $(NPM) run build

test: test-backend test-frontend

lint:
	$(PYTHON) -m ruff check backend/
	cd frontend && $(NPM) run build
