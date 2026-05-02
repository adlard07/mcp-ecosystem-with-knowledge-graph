from typing import List

from src.auth.api_keys.repository import (  # noqa: F401
    APIKeyRepository,
    get_api_key_record,
)

_repo = APIKeyRepository()


def create_api_key(user_id: str, name: str, scopes: List[str]) -> dict:
    return _repo.create_key(user_id, name, scopes)


def list_api_keys(user_id: str) -> List[dict]:
    return _repo.list_keys(user_id)


def revoke_api_key(key_id: str, user_id: str) -> None:
    _repo.revoke_key(key_id, user_id)
