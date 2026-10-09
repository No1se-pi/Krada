# MAX Mini Apps

Клиент подключает официальный `max-web-app.js`, вызывает `ready/expand` и передаёт неизменённую строку `window.WebApp.initData` в `/api/v1/auth/max`. Сервер URL-декодирует пары, запрещает дубли ключей, исключает `hash`, сортирует данные, строит `launch_params`, вычисляет `secret_key = HMAC-SHA256(key="WebAppData", message=bot token)`, сравнивает подпись constant-time и ограничивает возраст `auth_date` одним часом. `initDataUnsafe` не является доказательством личности.

Mini App существует внутри бота и production URL обязан использовать HTTPS. Deep-link payload не должен содержать секреты; он используется только как непривилегированный навигационный hint. Адаптер Bridge остаётся в frontend boundary, чтобы браузерный mock работал без MAX. Источники: [подключение](https://dev.max.ru/docs/webapps/introduction), [Bridge](https://dev.max.ru/docs/webapps/bridge), [валидация](https://dev.max.ru/docs/webapps/validation).

Mock endpoint существует только при `APP_ENV=local && ALLOW_MOCK_AUTH`; startup validation запрещает эту комбинацию в production.
