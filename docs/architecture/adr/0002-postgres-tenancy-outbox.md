# ADR-0002: PostgreSQL, shared-schema tenancy и outbox

Статус: принято. Одна PostgreSQL со `school_id` проще базы на школу и позволяет транзакционно связать игру, ledger и события. UUID исключает коллизии при будущем переносе. Application predicates обязательны, RLS добавляется перед pilot. Outbox выбран вместо dual write в брокер. Цена: нужны дисциплина tenant-context, publisher, retention и monitoring. Шардирование рассматривается только после измерений или требований изоляции.
