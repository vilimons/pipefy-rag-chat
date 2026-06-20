.PHONY: up down logs api-logs redis-logs test lint format ps

up:
	docker compose up --build

down:
	docker compose down

logs:
	docker compose logs -f

api-logs:
	docker compose logs -f api

redis-logs:
	docker compose logs -f redis

ps:
	docker compose ps

test:
	docker compose run --rm api pytest -q

lint:
	docker compose run --rm api ruff check app tests

format:
	docker compose run --rm api ruff format app tests
