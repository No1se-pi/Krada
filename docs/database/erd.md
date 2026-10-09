# ERD вертикального MVP

```mermaid
erDiagram
  SCHOOLS ||--o{ SCHOOL_CLASSES : contains
  SCHOOLS ||--o{ USERS : owns
  SCHOOL_CLASSES ||--o{ USERS : groups
  USERS ||--o{ EXTERNAL_IDENTITIES : authenticates
  USERS ||--o| CHARACTERS : plays
  CHARACTERS ||--o{ RAID_INSTANCES : enters
  RAID_INSTANCES ||--o| QUESTION_ATTEMPTS : resolves
  CHARACTERS ||--o{ WALLETS : owns
  WALLETS ||--o{ RESOURCE_LEDGER : records
  SCHOOLS ||--o{ OUTBOX_EVENTS : emits
```

Определения контента (`character_classes`, `questions`, `raid_definitions`) в MVP представлены версионируемой серверной конфигурацией, а не пустыми таблицами. Перенос в таблицы нужен вместе с редактором контента. Следующая миграция добавит versioned `courses → modules → topics → materials → questions`, inventory definitions/instances и RBAC.

Tenant-owned таблицы имеют `school_id` и индекс. Application-level фильтры обязательны. RLS запланирован как defence-in-depth: транзакция должна выполнять `SET LOCAL app.school_id`, политика сравнивает его с `school_id`; `SET LOCAL` критичен при pooling, чтобы tenant не протёк в следующую сессию.
