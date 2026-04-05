.PHONY: install run dev test lint clean docker-up docker-down

install:
	pip install -r requirements.txt

run:
	uvicorn app.main:app --host 0.0.0.0 --port 8000

dev:
	uvicorn app.main:app --reload --port 8000

test:
	pytest tests/ -v

lint:
	ruff check app/ tests/

clean:
	rm -rf outputs/reports/* outputs/testcases/* outputs/bdd/*.feature outputs/bdd/*_steps.py
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

docker-up:
	docker compose up --build -d

docker-down:
	docker compose down
