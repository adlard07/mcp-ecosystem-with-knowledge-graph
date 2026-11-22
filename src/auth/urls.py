"""FastAPI routes for authentication."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from src.models.auth import (
    AuthenticationServiceError,
    EmailAlreadyRegisteredError,
    InvalidCredentialsError,
    InvalidRefreshTokenError,
    InvalidSignupDataError,
    RefreshRequest,
    SigninRequest,
    SignupRequest,
    SignupResponse,
    TokenResponse,
)

from .auth import Authentication
from .login import login as login_service
from .signin import signin as signin_service
from .signup import signup as signup_service


router = APIRouter(tags=["authentication"], prefix="/auth")


def get_authenticator() -> Authentication:
    """Build the authentication service for one request."""
    try:
        return Authentication()
    except (AuthenticationServiceError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service is unavailable.",
        ) from exc


@router.post(
    "/signin",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Sign in with email and password",
)
def signin(
    request: SigninRequest,
    authenticator: Authentication = Depends(get_authenticator),
) -> TokenResponse:
    """Verify credentials and issue an access/refresh token pair."""
    try:
        tokens = signin_service(
            request.email,
            request.password,
            authenticator=authenticator,
        )
    except InvalidCredentialsError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except AuthenticationServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service is unavailable.",
        ) from exc
    return TokenResponse(**tokens)


@router.post(
    "/signup",
    response_model=SignupResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an account",
)
def signup(
    request: SignupRequest,
    authenticator: Authentication = Depends(get_authenticator),
) -> SignupResponse:
    """Create a user account and return its identifiers."""
    try:
        user = signup_service(
            request.firstname,
            request.lastname,
            request.email,
            request.password,
            authenticator=authenticator,
        )
    except InvalidSignupDataError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except EmailAlreadyRegisteredError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except AuthenticationServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service is unavailable.",
        ) from exc
    return SignupResponse(
        message="Account created.",
        first_name=user["first_name"],
        last_name=user["last_name"],
        user_id=str(user["user_id"]),
    )


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Refresh an authenticated session",
)
def login(
    request: RefreshRequest,
    authenticator: Authentication = Depends(get_authenticator),
) -> TokenResponse:
    """Validate and rotate a refresh token."""
    try:
        tokens = login_service(
            request.refresh_token,
            authenticator=authenticator,
        )
    except InvalidRefreshTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except AuthenticationServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service is unavailable.",
        ) from exc
    return TokenResponse(**tokens)


__all__ = ["get_authenticator", "login", "router", "signin", "signup"]
