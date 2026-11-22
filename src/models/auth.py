"""Authentication errors, token models, and request/response schemas."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from pydantic import BaseModel


class AuthenticationError(Exception):
    """Base exception for expected authentication failures."""


class InvalidCredentialsError(AuthenticationError):
    """Raised when an email and password do not match."""


class InvalidRefreshTokenError(AuthenticationError):
    """Raised when a refresh token is invalid, expired, or revoked."""


class AuthenticationServiceError(AuthenticationError):
    """Raised when authentication cannot complete due to configuration/DB errors."""


class EmailAlreadyRegisteredError(AuthenticationError):
    """Raised when a signup email is already in use."""


class InvalidSignupDataError(AuthenticationError):
    """Raised when signup fields are empty or malformed."""


@dataclass(frozen=True)
class TokenPair:
    """Access and refresh tokens returned after authentication."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"

    def as_dict(self) -> dict[str, str]:
        return {
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "token_type": self.token_type,
        }


class Token(BaseModel):
    """API token response model retained for existing callers."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenResponse(BaseModel):
    """Response returned by signin and refresh-token login endpoints."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Decoded JWT claims used by API layers."""

    sub: Optional[str] = None
    email: Optional[str] = None
    jti: Optional[str] = None
    type: Optional[str] = None


class LoginRequest(BaseModel):
    """Credential-login request payload."""

    email: str
    password: str


class SigninRequest(BaseModel):
    """Password-based signin request payload."""

    email: str
    password: str


class SignupRequest(BaseModel):
    """Account creation request payload."""

    firstname: str
    lastname: str
    email: str
    password: str


class RefreshRequest(BaseModel):
    """Refresh-token request payload."""

    refresh_token: str


class LogoutRequest(BaseModel):
    """Logout request payload."""

    refresh_token: str


class SignupResponse(BaseModel):
    """Signup response payload retained for existing callers."""

    message: str
    first_name: str
    last_name: str
    user_id: str


__all__ = [
    "AuthenticationError",
    "AuthenticationServiceError",
    "EmailAlreadyRegisteredError",
    "InvalidCredentialsError",
    "InvalidRefreshTokenError",
    "InvalidSignupDataError",
    "LoginRequest",
    "LogoutRequest",
    "RefreshRequest",
    "SigninRequest",
    "SignupRequest",
    "SignupResponse",
    "Token",
    "TokenData",
    "TokenPair",
    "TokenResponse",
]
