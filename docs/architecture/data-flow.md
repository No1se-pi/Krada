# Потоки данных

## Завершение рейда

```mermaid
sequenceDiagram
  participant W as Mini App
  participant A as API
  participant D as PostgreSQL
  participant O as Outbox publisher
  participant Q as RabbitMQ
  W->>A: POST /raids/{id}/answer + Idempotency-Key
  A->>D: BEGIN; lock raid + wallet
  A->>A: validate tenant/state; score answer
  A->>D: attempt + raid + XP + ledger + outbox
  A->>D: COMMIT
  A-->>W: result + reward
  O->>D: claim unpublished (planned)
  O->>Q: raid.completed / reward.granted (planned)
```

Повтор с тем же ключом возвращает сохранённый эффект без второго ledger entry. Повтор с другим ключом встречает терминальное состояние рейда.

## Аналитика

```mermaid
flowchart LR
  PG[(Operational PostgreSQL)] -->|outbox| MQ[RabbitMQ]
  MQ -->|idempotent consumer| GA[(Global analytics)]
  PG -->|cache fill| R[(Redis)]
  R -. miss / outage .-> PG
```
