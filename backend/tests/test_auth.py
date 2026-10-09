import hashlib
import hmac
import json
import time
from urllib.parse import urlencode

import pytest

from krada.auth import validate_max_init_data


def signed_data(token="test-token", **overrides):
    fields = {
        "auth_date": str(int(time.time())),
        "query_id": "q1",
        "user": json.dumps({"id": 42, "first_name": "Max"}, separators=(",", ":")),
        **overrides,
    }
    check = "\n".join(f"{key}={fields[key]}" for key in sorted(fields))
    secret = hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
    fields["hash"] = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
    return urlencode(fields)


def test_valid_max_payload():
    assert validate_max_init_data(signed_data(), "test-token")["user"]["id"] == 42


def test_tampering_and_expiry_are_rejected():
    with pytest.raises(ValueError):
        validate_max_init_data(signed_data().replace("Max", "Eve"), "test-token")
    with pytest.raises(ValueError, match="expired"):
        validate_max_init_data(signed_data(auth_date=str(int(time.time()) - 7200)), "test-token")


def test_duplicate_parameters_are_rejected():
    with pytest.raises(ValueError, match="duplicate"):
        validate_max_init_data(signed_data() + "&user=evil", "test-token")


def test_max_user_requires_integer_platform_id():
    with pytest.raises(ValueError, match="invalid_max_user"):
        validate_max_init_data(signed_data(user=json.dumps({"id": "not-an-integer"})), "test-token")
