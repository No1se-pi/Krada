import hashlib
import hmac
import json
import time
import uuid
from dataclasses import dataclass
from typing import Any
from urllib.parse import parse_qsl

import jwt
from fastapi import Depends, Header, HTTPException

from krada.config import Settings, get_settings
from krada.tenancy import TenantContext


@dataclass(frozen=True, slots=True)
class Principal:
    """Authenticated actor plus the trusted tenant assigned by the server."""

    user_id: uuid.UUID
    tenant: TenantContext
    role: str


def validate_max_init_data(
    init_data: str, bot_token: str, max_age_seconds: int = 3600
) -> dict[str, Any]:
    """Validate MAX WebAppData using the documented two-stage HMAC algorithm.

    Duplicate parameters are rejected before converting pairs to a dictionary. Otherwise an
    attacker could make the verifier and application disagree about which value is authoritative.
    """
    pairs = parse_qsl(init_data, keep_blank_values=True)
    if len({key for key, _ in pairs}) != len(pairs):
        raise ValueError("duplicate_max_parameter")
    fields: dict[str, Any] = dict(pairs)
    supplied_hash = fields.pop("hash", "")
    if not supplied_hash or not bot_token:
        raise ValueError("invalid_max_data")
    data_check = "\n".join(f"{key}={fields[key]}" for key in sorted(fields))
    secret = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    expected = hmac.new(secret, data_check.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, supplied_hash):
        raise ValueError("invalid_max_signature")
    auth_date = int(fields.get("auth_date", "0"))
    if auth_date > int(time.time()) + 30 or int(time.time()) - auth_date > max_age_seconds:
        raise ValueError("expired_max_data")
    user = json.loads(fields["user"])
    if not isinstance(user, dict) or not isinstance(user.get("id"), int):
        raise ValueError("invalid_max_user")
    fields["user"] = user
    return fields


def issue_token(user_id: uuid.UUID, school_id: uuid.UUID, role: str, settings: Settings) -> str:
    """Issue a signed application session after identity and membership resolution."""
    now = int(time.time())
    return jwt.encode(
        {
            "sub": str(user_id),
            "school_id": str(school_id),
            "role": role,
            "iss": "krada-api",
            "aud": "krada-mini-app",
            "iat": now,
            "exp": now + 86400,
        },
        settings.session_secret,
        algorithm="HS256",
    )


def current_principal(
    authorization: str = Header(), settings: Settings = Depends(get_settings)
) -> Principal:
    try:
        scheme, token = authorization.split(" ", 1)
        if scheme.lower() != "bearer":
            raise ValueError
        # Issuer and audience prevent a valid token from another application context from being
        # accepted merely because both applications accidentally share a signing secret.
        data = jwt.decode(
            token,
            settings.session_secret,
            algorithms=["HS256"],
            issuer="krada-api",
            audience="krada-mini-app",
        )
        return Principal(
            user_id=uuid.UUID(data["sub"]),
            tenant=TenantContext(school_id=uuid.UUID(data["school_id"])),
            role=data["role"],
        )
    except (ValueError, KeyError, jwt.PyJWTError) as exc:
        raise HTTPException(
            401, detail={"code": "invalid_session", "message": "Сессия недействительна"}
        ) from exc
