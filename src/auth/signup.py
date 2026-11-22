"""Account creation entry point."""

from __future__ import annotations

from typing import Any, Optional

from psycopg2.errors import UniqueViolation

from src.models.auth import (
    AuthenticationServiceError,
    EmailAlreadyRegisteredError,
    InvalidSignupDataError,
)

from .auth import Authentication


def signup(
    firstname: str,
    lastname: str,
    email: str,
    password: str,
    *,
    authenticator: Optional[Authentication] = None,
) -> dict[str, Any]:
    """Create a user with a hashed password and an empty refresh digest."""
    service = authenticator or Authentication()
    normalized_first_name = _required_name(firstname, "First name")
    normalized_last_name = _required_name(lastname, "Last name")
    normalized_email = _required_email(email)
    _validate_password(password)

    if _email_exists(service, normalized_email):
        raise EmailAlreadyRegisteredError("Email is already registered.")

    values = {
        "first_name": normalized_first_name,
        "last_name": normalized_last_name,
        "email": normalized_email,
        "password_hash": service.hash_password(password),
        "rf_token": "",
    }

    try:
        return service.database.insert("users", values)
    except UniqueViolation as exc:
        raise EmailAlreadyRegisteredError("Email is already registered.") from exc
    except Exception as exc:
        raise AuthenticationServiceError(
            "Authentication service is unavailable."
        ) from exc


def _email_exists(service: Authentication, email: str) -> bool:
    try:
        rows = service.database.fetch(
            "users",
            {"email": email},
            columns=("user_id",),
        )
    except Exception as exc:
        raise AuthenticationServiceError(
            "Authentication service is unavailable."
        ) from exc
    return bool(rows)


def _required_name(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise InvalidSignupDataError(f"{label} is required.")
    return value.strip()


def _required_email(value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise InvalidSignupDataError("Email is required.")
    return value.strip()


def _validate_password(password: Any) -> None:
    if not isinstance(password, str) or not password:
        raise InvalidSignupDataError("Password is required.")


__all__ = ["signup"]
