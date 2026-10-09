from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from krada.database import Base, get_db
from krada.main import app


def test_api_vertical_flow_and_reconnect_snapshot():
    """Exercise routing, DTOs, auth, idempotency, and the reconnect projection together."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)

    def override_db() -> Generator[Session, None, None]:
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_db] = override_db
    try:
        with TestClient(app) as client:
            login = client.post("/api/v1/auth/mock", json={"display_name": "Добрыня"})
            assert login.status_code == 200
            headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

            # Mutations that can create value reject clients without an idempotency contract.
            missing_key = client.post(
                "/api/v1/characters",
                headers=headers,
                json={"name": "Ратибор", "class_key": "mage"},
            )
            assert missing_key.status_code == 422
            assert missing_key.json()["detail"]["code"] == "validation_error"

            character = client.post(
                "/api/v1/characters",
                headers={**headers, "Idempotency-Key": "character-key"},
                json={"name": "Ратибор", "class_key": "mage"},
            )
            assert character.status_code == 201

            raid = client.post(
                "/api/v1/raids",
                headers={**headers, "Idempotency-Key": "raid-start-key"},
            )
            assert raid.status_code == 201
            raid_body = raid.json()
            assert "correct_answer" not in raid_body["question"]
            assert "explanation" not in raid_body["question"]

            # `/me` is sufficient to recover the active raid after WebView suspension.
            dashboard = client.get("/api/v1/me", headers=headers)
            assert dashboard.json()["active_raid"]["id"] == raid_body["id"]

            answer_headers = {**headers, "Idempotency-Key": "raid-answer-key"}
            first = client.post(
                f"/api/v1/raids/{raid_body['id']}/answer",
                headers=answer_headers,
                json={"answer": "988"},
            )
            replay = client.post(
                f"/api/v1/raids/{raid_body['id']}/answer",
                headers=answer_headers,
                json={"answer": "changed retry body"},
            )
            assert first.status_code == replay.status_code == 200
            assert first.json() == replay.json()
    finally:
        app.dependency_overrides.clear()
