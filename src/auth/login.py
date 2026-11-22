"""Refresh-token login entry point."""

from __future__ import annotations

import hmac
from typing import Any, Mapping, Optional

from jose import JWTError, jwt

from src.models.auth import (
    AuthenticationServiceError,
    InvalidRefreshTokenError,
)

from .auth import Authentication


def login(
    refresh_token: str,
    *,
    authenticator: Optional[Authentication] = None,
) -> dict[str, str]:
    """Validate and rotate a refresh token, returning a new token pair."""
    service = authenticator or Authentication()
    claims = _decode_refresh_token(service, refresh_token)
    user_id = claims.get("sub")
    if not isinstance(user_id, str) or not user_id:
        raise InvalidRefreshTokenError("Invalid refresh token.")

    try:
        rows = service.database.fetch(
            "users",
            {"user_id": user_id},
            columns=service._user_columns,
        )
    except Exception as exc:
        raise AuthenticationServiceError(
            "Authentication service is unavailable."
        ) from exc

    if not rows:
        raise InvalidRefreshTokenError("Invalid refresh token.")

    stored_digest = rows[0].get("rf_token")
    presented_digest = service._digest_refresh_token(refresh_token)
    if not isinstance(stored_digest, str) or not hmac.compare_digest(
        stored_digest,
        presented_digest,
    ):
        raise InvalidRefreshTokenError("Invalid refresh token.")

    token_pair = service._issue_tokens(user_id)
    service._persist_refresh_token(
        user_id,
        token_pair.refresh_token,
        expected_digest=presented_digest,
    )
    return token_pair.as_dict()


def _decode_refresh_token(
    service: Authentication,
    refresh_token: str,
) -> Mapping[str, Any]:
    if not isinstance(refresh_token, str) or not refresh_token.strip():
        raise InvalidRefreshTokenError("Invalid refresh token.")
    try:
        claims = jwt.decode(
            refresh_token,
            service.secret_key,
            algorithms=[service.algorithm],
        )
    except (JWTError, TypeError, ValueError) as exc:
        raise InvalidRefreshTokenError("Invalid refresh token.") from exc

    if claims.get("type") != "refresh" or not claims.get("sub"):
        raise InvalidRefreshTokenError("Invalid refresh token.")
    return claims


__all__ = ["login"]
