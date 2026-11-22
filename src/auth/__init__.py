"""Authentication components."""

from pathlib import Path

from dotenv import load_dotenv


load_dotenv(Path(__file__).resolve().parents[2] / ".env")

from src.models.auth import (
    AuthenticationError,
    AuthenticationServiceError,
    EmailAlreadyRegisteredError,
    InvalidCredentialsError,
    InvalidRefreshTokenError,
    InvalidSignupDataError,
    TokenPair,
)

from .auth import Authentication
from .login import login
from .signin import signin
from .signup import signup

__all__ = [
    "Authentication",
    "AuthenticationError",
    "AuthenticationServiceError",
    "EmailAlreadyRegisteredError",
    "InvalidCredentialsError",
    "InvalidRefreshTokenError",
    "InvalidSignupDataError",
    "TokenPair",
    "login",
    "signin",
    "signup",
]
