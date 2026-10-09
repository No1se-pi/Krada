# REST API v1

Базовый путь: `/api/v1`. OpenAPI доступен на `/docs` вне production.

Все защищённые запросы используют `Authorization: Bearer <session>`. Tenant определяется только подписанной сессией. Клиент не передаёт `school_id` в игровых DTO.

Операции создания персонажа, старта рейда и ответа требуют `Idempotency-Key` длиной 8–128 символов. Клиент повторяет тот же ключ после неопределённого сетевого сбоя. Сервер связывает ключ с tenant, actor, operation и entity, затем хранит только SHA-256 hash.

Ошибки имеют единый envelope:

```json
{
  "detail": {
    "code": "validation_error",
    "message": "Проверьте введённые данные",
    "fields": [{"location": ["header", "idempotency-key"], "type": "missing"}]
  }
}
```

Реализованные группы: `/auth`, `/characters`, `/character-classes`, `/raids`, `/leaderboards` и reconnect snapshot `/me`. Остальные группы из целевой архитектуры добавляются только вместе с реальной моделью и миграцией.
