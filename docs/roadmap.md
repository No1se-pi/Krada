# План реализации

1. **A/B — текущий проход:** monorepo, Compose, миграция, health, MAX/mock auth, герой, одиночный рейд, ledger/outbox, мобильный UI, unit tests и архитектурная документация.
2. **B hardening:** PostgreSQL integration/E2E, RLS, Redis rate limit/cache, outbox publisher с retry/DLQ, worker, bot webhook, metrics, backup/restore drill.
3. **C:** inventory и artifact effect registry, versioned content, дополнительные рейды, teacher RBAC/UI, deterministic visuals.
4. **D:** безопасный upload/RAG pipeline, review/publish, AI fallback, отдельные analytics projections.
5. **E:** load/isolation/security testing, tracing/dashboards, chaos scenarios, privacy process, production runbooks и core freeze 30 октября 2026.

Дедлайн рабочей версии по ТЗ — 6 ноября 2026. Самый рискованный путь — production onboarding MAX и проверка прав/бота, поэтому его следует испытать до расширения механик.
