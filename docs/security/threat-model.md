# Модель угроз

Активы: личности несовершеннолетних, членство в школе, учебные результаты, прогресс и ledger. Границы доверия: WebView/API, API/БД, worker/broker, teacher uploads/AI.

Основные меры: HMAC и freshness для MAX; короткоживущий подписанный session token; object-level tenant predicates; Pydantic allow-list DTO; server-authoritative state/rewards; row locks и idempotency uniqueness; audit/outbox без PII; CORS allow-list и security headers; secrets только из environment. Для production ещё обязательны: managed secret rotation, CSRF assessment для выбранной модели токена, Redis rate limiting, RLS tests, webhook signature/replay guard, malware/MIME/size scanning uploads, retention/export/delete process и юридическая проверка 152-ФЗ и требований к данным детей.

Критический residual risk MVP: bearer token хранится в `sessionStorage`, поэтому доступный на странице вредоносный скрипт сможет его прочитать. CSP уменьшает риск, но перед pilot следует перейти на платформенно обновляемую короткую сессию или защищённую HttpOnly cookie с CSRF-защитой. Нельзя писать initData, bot token, ответы учащихся и полные профили в логи/аналитику. Production reverse proxy обязан повторить security headers из `vite.config.ts` — Vite не является production-сервером.
