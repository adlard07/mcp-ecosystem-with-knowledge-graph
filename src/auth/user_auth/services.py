from typing import Optional, Tuple

from dotenv import load_dotenv
from fastapi import Depends

from src.auth.user_auth.repository import (
    _ACCESS_EXPIRE_MINUTES,
    AuthenticationRepository,
)

load_dotenv(override=True)

_repo = AuthenticationRepository()

oauth2_scheme = _repo.oauth2_scheme


def hash_password(plain: str) -> str:
    return _repo.hash_password(plain)


def authenticate_user(email: str, password: str) -> Optional[dict]:
    return _repo.authenticate_user(email, password)


def create_access_token(user_id: str, email: str) -> Tuple[str, str]:
    return _repo.create_access_token(user_id, email)


def create_refresh_token(user_id: str) -> Tuple[str, str]:
    return _repo.create_refresh_token(user_id)


def rotate_refresh_token(raw_token: str) -> Tuple[str, str, dict]:
    return _repo.rotate_refresh_token(raw_token)


def revoke_refresh_token(raw_token: str) -> None:
    _repo.revoke_refresh_token(raw_token)


def revoke_all_sessions(user_id: str) -> int:
    return _repo.revoke_all_sessions(user_id)


async def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    return await _repo.get_current_user(token)


async def get_current_active_user(
    current_user: dict = Depends(get_current_user),
) -> dict:
    return await _repo.get_current_active_user(current_user)


def generate_csrf_token() -> str:
    return _repo.generate_csrf_token()


def validate_csrf_token(cookie_token: str, header_token: str) -> bool:
    return _repo.validate_csrf_token(cookie_token, header_token)
