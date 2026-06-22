.PHONY: help up down down-volumes restart ps logs api-logs frontend-logs redis-logs \
	test lint format frontend-build frontend-install validate build clean-model-cache

help:
	@echo ""
	@echo "Pipefy RAG Chat - comandos disponíveis"
	@echo ""
	@echo "  make up               Sobe frontend, API e Redis"
	@echo "  make down             Para os containers mantendo volumes"
	@echo "  make down-volumes     Para containers e remove volumes"
	@echo "  make restart          Reinicia a stack"
	@echo "  make ps               Lista containers"
	@echo "  make logs             Mostra logs de todos os serviços"
	@echo "  make api-logs         Mostra logs da API"
	@echo "  make frontend-logs    Mostra logs do frontend"
	@echo "  make redis-logs       Mostra logs do Redis"
	@echo ""
	@echo "  make test             Roda testes do backend sem LangSmith"
	@echo "  make lint             Roda Ruff no backend sem LangSmith"
	@echo "  make format           Formata backend com Ruff"
	@echo "  make frontend-build   Valida build do frontend"
	@echo "  make validate         Roda test + lint + frontend-build"
	@echo ""
	@echo "  make build            Builda imagens Docker"
	@echo "  make clean-model-cache Remove cache local de modelos Docker"
	@echo ""

up:
	docker compose up --build

down:
	docker compose down

down-volumes:
	docker compose down -v

restart:
	docker compose down
	docker compose up --build

ps:
	docker compose ps

logs:
	docker compose logs -f

api-logs:
	docker compose logs -f api

frontend-logs:
	docker compose logs -f frontend

redis-logs:
	docker compose logs -f redis

test:
	docker compose run --rm -e LANGSMITH_TRACING=false api pytest -q tests

lint:
	docker compose run --rm -e LANGSMITH_TRACING=false api ruff check app tests

format:
	docker compose run --rm -e LANGSMITH_TRACING=false api ruff format app tests
	docker compose run --rm -e LANGSMITH_TRACING=false api ruff check app tests --fix

frontend-install:
	cd frontend && npm install

frontend-build:
	cd frontend && npm run build

validate: test lint frontend-build

build:
	docker compose build api frontend

clean-model-cache:
	docker volume rm pipefy-rag-chat_model_cache || true
