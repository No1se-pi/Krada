# Локальная разработка и эксплуатация

1. Скопировать `.env.example` в `.env`.
2. Выполнить `docker compose up --build`.
3. Открыть http://localhost:5173; Swagger доступен на http://localhost:8000/docs.
4. Для сброса демо-данных остановить compose и удалить только именованный volume проекта командой `docker compose down -v` (операция необратима).

Backend перед стартом выполняет `alembic upgrade head`. Liveness не проверяет зависимости; readiness делает `SELECT 1`. RabbitMQ UI: http://localhost:15672 (`krada/krada` только локально). Production требует HTTPS reverse proxy, отдельные секреты, закрытые порты БД/Redis/RabbitMQ/MinIO, backup policy и проверенный restore.

Диагностика: `docker compose ps`, затем `docker compose logs backend`. Если readiness 503 — проверить миграцию и PostgreSQL. Если MAX login 401 — проверить bot token, clock skew, freshness и не логировать сам initData.
