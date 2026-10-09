import pytest
from pydantic import ValidationError

from krada.config import Settings


def test_cors_allow_list_is_explicitly_split():
    settings = Settings(cors_origins="https://one.example,https://two.example")
    assert settings.cors_origin_list == ["https://one.example", "https://two.example"]


def test_mock_auth_is_rejected_in_production():
    with pytest.raises(ValidationError, match="Mock authentication"):
        Settings(app_env="production", allow_mock_auth=True)
