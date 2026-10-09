# Крада

Каркас образовательной RPG для MAX Mini Apps: модульный монолит на FastAPI/PostgreSQL и мобильный React-клиент. Первый вертикальный сценарий проходит через доменные правила: локальный вход → персонаж → рейд → вопрос → результат → идемпотентная награда → рейтинг.

## Быстрый запуск

Требуется Docker Desktop.

```bash
copy .env.example .env
docker compose up --build
```

- игра: http://localhost:5173
- API и Swagger: http://localhost:8000/docs
- health: http://localhost:8000/health/ready

Локальный вход доступен только при `APP_ENV=local` и `ALLOW_MOCK_AUTH=true`. В production приложение завершится с ошибкой при такой комбинации.

## Разработка без Docker

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
pytest
uvicorn krada.main:app --reload
```

```bash
cd frontend
npm install
npm run dev
```

Команды качества: `make test`, `make lint`, `make check`. Архитектура и решения описаны в [docs/architecture/overview.md](docs/architecture/overview.md).

## Статус

Это фундамент и вертикальный MVP, а не вся игра. Реализованы core-сущности и один тип одиночного рейда. Redis/RabbitMQ/MinIO подняты инфраструктурно; outbox хранится транзакционно, а публикация и AI/RAG-задачи — следующий этап. Подробный отчёт — [docs/testing/test-results.md](docs/testing/test-results.md).
Игра - проект для Хакатона "Идея Фикс"
