"""Password-based signin entry point."""

from __future__ import annotations

from typing import Any, Mapping, Optional

from src.models.auth import (
    AuthenticationServiceError,
    InvalidCredentialsError,
)

from .auth import Authentication


def signin(
    email: str,
    password: str,
    *,
    authenticator: Optional[Authentication] = None,
) -> dict[str, str]:
    """Verify credentials, persist a refresh digest, and return token pair."""
    service = authenticator or Authentication()
    normalized_email = service._validate_email(email)
    service._validate_password(password)

    try:
        user = _find_user(service, normalized_email)
    except Exception as exc:
        raise AuthenticationServiceError(
            "Authentication service is unavailable."
        ) from exc

    if not user or not _verify_password(service, password, user.get("password_hash")):
        raise InvalidCredentialsError("Invalid credentials.")

    token_pair = service._issue_tokens(user["user_id"])
    service._persist_refresh_token(user["user_id"], token_pair.refresh_token)
    return token_pair.as_dict()


def _find_user(
    service: Authentication,
    email: str,
) -> Optional[Mapping[str, Any]]:
    rows = service.database.fetch(
        "users",
        {"email": email},
        columns=service._user_columns,
    )
    return rows[0] if rows else None


def _verify_password(
    service: Authentication,
    password: str,
    password_hash: Any,
) -> bool:
    if not isinstance(password_hash, str) or not password_hash:
        return False
    try:
        return service._passwords.verify(password, password_hash)
    except (ValueError, TypeError):
        return False


__all__ = ["signin"]
