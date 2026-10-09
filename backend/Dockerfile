FROM python:3.12-slim AS base
WORKDIR /app
COPY pyproject.toml alembic.ini ./
COPY src ./src
COPY migrations ./migrations

FROM base AS development
RUN pip install --no-cache-dir ".[dev]"
COPY tests ./tests
CMD ["sh", "-c", "alembic upgrade head && uvicorn krada.main:app --host 0.0.0.0 --port 8000"]

FROM base AS production
RUN pip install --no-cache-dir .
CMD ["sh", "-c", "alembic upgrade head && uvicorn krada.main:app --host 0.0.0.0 --port 8000"]
