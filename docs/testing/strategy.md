# Стратегия тестирования

Unit: state machine, scoring, registries и MAX HMAC. Integration с PostgreSQL: миграции, tenant isolation, row locks, idempotency и outbox atomicity. API: DTO/error contracts и отсутствие correct answer. E2E: mock login → hero → raid → reward → leaderboard. Security: cross-school UUID, duplicate MAX fields, expired signature, replay and rate-limit. Load: 100 concurrent users with 80/20 read/write mix; record p50/p95/p99, DB pool, CPU/RAM and queue depth. Цели из ТЗ (<300 ms read, <500 ms state change) не считаются подтверждёнными до такого прогона.
