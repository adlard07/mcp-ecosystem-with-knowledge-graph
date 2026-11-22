"""Credential authentication and access/refresh token management."""

from __future__ import annotations

import hashlib
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Optional

from jose import jwt
from passlib.context import CryptContext

from src.database.supabase import SupabaseOps
from src.models.auth import (
    AuthenticationError,
    AuthenticationServiceError,
    InvalidCredentialsError,
    InvalidRefreshTokenError,
    TokenPair,
)


class Authentication:
    """Authenticate users and issue revocable access and refresh tokens.

    Refresh tokens are returned to the caller but only their SHA-256 digest is
    persisted in ``users.rf_token``. This allows token revocation without
    storing a reusable bearer credential in the database.
    """

    _user_columns = (
        "user_id",
        "first_name",
        "last_name",
        "email",
        "password_hash",
        "rf_token",
    )

    def __init__(
        self,
        database: Optional[SupabaseOps] = None,
        *,
        secret_key: Optional[str] = None,
        algorithm: Optional[str] = None,
        access_token_expire_minutes: Optional[int] = None,
        refresh_token_expire_days: Optional[int] = None,
        now: Optional[Callable[[], datetime]] = None,
    ) -> None:
        self.database = database or SupabaseOps()
        self.secret_key = secret_key or os.getenv("JWT_SECRET_KEY")
        if not self.secret_key or len(self.secret_key) < 32:
            raise AuthenticationServiceError(
                "JWT_SECRET_KEY must be configured with at least 32 characters."
            )

        self.algorithm = algorithm or os.getenv("JWT_ALGORITHM", "HS256")
        self.access_token_expire_minutes = self._positive_int(
            access_token_expire_minutes,
            os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15"),
            "ACCESS_TOKEN_EXPIRE_MINUTES",
        )
        self.refresh_token_expire_days = self._positive_int(
            refresh_token_expire_days,
            os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "30"),
            "REFRESH_TOKEN_EXPIRE_DAYS",
        )
        self._now = now or (lambda: datetime.now(timezone.utc))
        # PBKDF2 is provided by passlib itself and produces a hash that fits
        # the widened password_hash column without requiring another backend.
        self._passwords = CryptContext(
            schemes=["pbkdf2_sha256"],
            deprecated="auto",
        )

    @staticmethod
    def _positive_int(value: Optional[int], fallback: str, name: str) -> int:
        candidate: Any = fallback if value is None else value
        try:
            parsed = int(candidate)
        except (TypeError, ValueError) as exc:
            raise AuthenticationServiceError(f"{name} must be a positive integer.") from exc
        if parsed <= 0:
            raise AuthenticationServiceError(f"{name} must be a positive integer.")
        return parsed

    def hash_password(self, password: str) -> str:
        """Return a one-way password hash suitable for ``users.password_hash``."""
        self._validate_password(password)
        return self._passwords.hash(password)

    def signin(self, email: str, password: str) -> dict[str, str]:
        """Delegate credential authentication to :mod:`src.auth.signin`."""
        from .signin import signin as signin_function

        return signin_function(email, password, authenticator=self)

    def signup(
        self,
        firstname: str,
        lastname: str,
        email: str,
        password: str,
    ) -> dict[str, Any]:
        """Delegate account creation to :mod:`src.auth.signup`."""
        from .signup import signup as signup_function

        return signup_function(
            firstname,
            lastname,
            email,
            password,
            authenticator=self,
        )

    def login(self, refresh_token: str) -> dict[str, str]:
        """Delegate refresh-token login to :mod:`src.auth.login`."""
        from .login import login as login_function

        return login_function(refresh_token, authenticator=self)

    def refresh_access_token(self, refresh_token: str) -> dict[str, str]:
        """Backward-compatible delegate for refresh-token login."""
        return self.login(refresh_token)

    def _issue_tokens(self, user_id: Any) -> TokenPair:
        issued_at = self._utc_now()
        issued_timestamp = int(issued_at.timestamp())
        subject = str(user_id)

        access_claims = {
            "sub": subject,
            "type": "access",
            "iat": issued_timestamp,
            "exp": int(
                (issued_at + timedelta(minutes=self.access_token_expire_minutes)).timestamp()
            ),
            "jti": secrets.token_urlsafe(16),
        }
        refresh_claims = {
            "sub": subject,
            "type": "refresh",
            "iat": issued_timestamp,
            "exp": int(
                (issued_at + timedelta(days=self.refresh_token_expire_days)).timestamp()
            ),
            "jti": secrets.token_urlsafe(32),
        }

        return TokenPair(
            access_token=jwt.encode(
                access_claims,
                self.secret_key,
                algorithm=self.algorithm,
            ),
            refresh_token=jwt.encode(
                refresh_claims,
                self.secret_key,
                algorithm=self.algorithm,
            ),
        )

    def _persist_refresh_token(
        self,
        user_id: Any,
        refresh_token: str,
        *,
        expected_digest: Optional[str] = None,
    ) -> None:
        filters: dict[str, Any] = {"user_id": user_id}
        if expected_digest is not None:
            filters["rf_token"] = expected_digest
        try:
            updated = self.database.update(
                "users",
                {"rf_token": self._digest_refresh_token(refresh_token)},
                filters,
            )
        except Exception as exc:
            raise AuthenticationServiceError(
                "Authentication service is unavailable."
            ) from exc
        if updated != 1:
            if expected_digest is not None:
                raise InvalidRefreshTokenError("Invalid refresh token.")
            raise AuthenticationServiceError(
                "Authentication service is unavailable."
            )

    @staticmethod
    def _digest_refresh_token(refresh_token: str) -> str:
        return hashlib.sha256(refresh_token.encode("utf-8")).hexdigest()

    def _utc_now(self) -> datetime:
        current = self._now()
        if current.tzinfo is None:
            return current.replace(tzinfo=timezone.utc)
        return current.astimezone(timezone.utc)

    @staticmethod
    def _validate_email(email: str) -> str:
        if not isinstance(email, str):
            raise InvalidCredentialsError("Invalid credentials.")
        normalized = email.strip()
        if not normalized:
            raise InvalidCredentialsError("Invalid credentials.")
        return normalized

    @staticmethod
    def _validate_password(password: str) -> None:
        if not isinstance(password, str) or not password:
            raise InvalidCredentialsError("Invalid credentials.")


def signin(
    email: str,
    password: str,
    *,
    authenticator: Optional[Authentication] = None,
) -> dict[str, str]:
    """Backward-compatible wrapper; implementation lives in ``signin.py``."""
    from .signin import signin as signin_function

    return signin_function(
        email,
        password,
        authenticator=authenticator,
    )


def login(
    refresh_token: str,
    *,
    authenticator: Optional[Authentication] = None,
) -> dict[str, str]:
    """Backward-compatible wrapper; implementation lives in ``login.py``."""
    from .login import login as login_function

    return login_function(refresh_token, authenticator=authenticator)


__all__ = [
    "Authentication",
    "AuthenticationError",
    "AuthenticationServiceError",
    "InvalidCredentialsError",
    "InvalidRefreshTokenError",
    "TokenPair",
    "login",
    "signin",
]
