# Результаты проверок

Дата последнего прогона: 9 октября 2026.

- `pytest`: 14 passed (доменное ядро, MAX signature/config, service integration и полный API-flow).
- `ruff check`: passed.
- `mypy src`: passed, 17 source files checked.
- `npm run lint`: passed.
- `npm test`: 1 passed (stable idempotency key after an ambiguous network failure).
- `npm run build`: passed; production bundle 274.03 kB JS (84.83 kB gzip).
- `npm audit`: 0 vulnerabilities, включая dev dependencies.
- `alembic upgrade head --sql`: обе миграции успешно формируют PostgreSQL DDL.
- `docker compose config --quiet`: passed.
- Docker smoke-test: не выполнен — локальный Docker Desktop engine был недоступен.

Есть SQLite integration/API tests, включая cross-tenant denial и идемпотентный replay. PostgreSQL concurrency/RLS, браузерный E2E и load suites остаются обязательными до пилота. Целевые latency из ТЗ не подтверждены.
