.PHONY: up down test lint check migrate
up:
	docker compose up --build
down:
	docker compose down
test:
	docker compose run --rm backend pytest
lint:
	docker compose run --rm backend ruff check .
	docker compose run --rm frontend npm run lint
check: lint test
	docker compose run --rm frontend npm run build
migrate:
	docker compose run --rm backend alembic upgrade head
