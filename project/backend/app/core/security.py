"""Password hashing and signed access tokens for the web client.

The project deliberately keeps this module dependency-free: PBKDF2 and
HMAC-SHA256 from the standard library are enough for the prototype and avoid
pulling a JWT framework into the backend just for one token type.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from uuid import UUID

from app.core.config import settings

_PBKDF2_ITERATIONS = 300_000
_PBKDF2_PREFIX = "pbkdf2_sha256"


class InvalidTokenError(ValueError):
    """Raised when an access token is malformed, tampered with or expired."""


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    try:
        return base64.urlsafe_b64decode(value + padding)
    except (ValueError, TypeError) as exc:
        raise InvalidTokenError("malformed_token") from exc


def hash_password(password: str) -> str:
    if not password:
        raise ValueError("password_must_not_be_empty")
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        _PBKDF2_ITERATIONS,
    )
    return "$".join(
        (
            _PBKDF2_PREFIX,
            str(_PBKDF2_ITERATIONS),
            _b64url_encode(salt),
            _b64url_encode(digest),
        )
    )


def verify_password(password: str, encoded: str | None) -> bool:
    if not password or not encoded:
        return False
    try:
        prefix, iterations_raw, salt_raw, digest_raw = encoded.split("$", 3)
        if prefix != _PBKDF2_PREFIX:
            return False
        iterations = int(iterations_raw)
        if iterations < 100_000 or iterations > 2_000_000:
            return False
        salt = _b64url_decode(salt_raw)
        expected = _b64url_decode(digest_raw)
    except (ValueError, InvalidTokenError):
        return False

    actual = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        iterations,
    )
    return hmac.compare_digest(actual, expected)


def create_access_token(user_id: UUID, ttl_seconds: int | None = None) -> str:
    now = int(time.time())
    ttl = ttl_seconds if ttl_seconds is not None else settings.web_token_ttl_seconds
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + max(60, int(ttl)),
    }
    signing_input = ".".join(
        (
            _b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8")),
            _b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8")),
        )
    )
    signature = hmac.new(
        settings.web_auth_secret.encode("utf-8"),
        signing_input.encode("ascii"),
        hashlib.sha256,
    ).digest()
    return f"{signing_input}.{_b64url_encode(signature)}"


def decode_access_token(token: str) -> UUID:
    parts = token.split(".")
    if len(parts) != 3:
        raise InvalidTokenError("malformed_token")

    header_raw, payload_raw, signature_raw = parts
    signing_input = f"{header_raw}.{payload_raw}".encode("ascii")
    expected_signature = hmac.new(
        settings.web_auth_secret.encode("utf-8"),
        signing_input,
        hashlib.sha256,
    ).digest()

    try:
        actual_signature = _b64url_decode(signature_raw)
    except InvalidTokenError as exc:
        raise InvalidTokenError("malformed_signature") from exc

    if not hmac.compare_digest(actual_signature, expected_signature):
        raise InvalidTokenError("invalid_signature")

    try:
        header = json.loads(_b64url_decode(header_raw))
        payload = json.loads(_b64url_decode(payload_raw))
    except (ValueError, TypeError, json.JSONDecodeError) as exc:
        raise InvalidTokenError("malformed_payload") from exc

    if not isinstance(header, dict) or header.get("alg") != "HS256":
        raise InvalidTokenError("unsupported_algorithm")
    if not isinstance(payload, dict):
        raise InvalidTokenError("malformed_payload")

    expires_at = payload.get("exp")
    if not isinstance(expires_at, (int, float)) or int(expires_at) <= int(time.time()):
        raise InvalidTokenError("token_expired")

    subject = payload.get("sub")
    if not isinstance(subject, str):
        raise InvalidTokenError("missing_subject")
    try:
        return UUID(subject)
    except ValueError as exc:
        raise InvalidTokenError("invalid_subject") from exc
