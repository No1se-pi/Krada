import pytest
from pydantic import ValidationError

from krada.config import Settings


def test_cors_allow_list_is_explicitly_split():
    settings = Settings(cors_origins="https://one.example,https://two.example")
    assert settings.cors_origin_list == ["https://one.example", "https://two.example"]


def test_mock_auth_is_rejected_in_production():
    with pytest.raises(ValidationError, match="Mock authentication"):
        Settings(app_env="production", allow_mock_auth=True)


def test_production_requires_max_token_and_https_cors():
    with pytest.raises(ValidationError, match="MAX_BOT_TOKEN"):
        Settings(
            app_env="production",
            allow_mock_auth=False,
            session_secret="a-strong-production-secret-with-32-chars",
            max_bot_token="",
            cors_origins="https://game.example",
        )
    with pytest.raises(ValidationError, match="HTTPS"):
        Settings(
            app_env="production",
            allow_mock_auth=False,
            session_secret="a-strong-production-secret-with-32-chars",
            max_bot_token="real-token",
            cors_origins="*",
        )
