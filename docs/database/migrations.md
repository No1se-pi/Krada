# Миграции

Миграции Alembic применяются строго по порядку перед запуском API.

- `0001_vertical_mvp` создаёт tenant, identity, character, raid, attempt, wallet, ledger и outbox.
- `0002_harden_idempotency` добавляет scoped operation key, единственный активный рейд на персонажа и неизменяемый снимок выданной награды.

Для проверки без подключения: `python -m alembic upgrade head --sql`. Перед production-миграцией обязательны backup, rehearsal на копии данных и проверка downgrade/forward-fix стратегии. DDL `0002` рассчитан на короткий MVP-набор; на большой таблице создание индексов следует заменить отдельным online/concurrent rollout.
