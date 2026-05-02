import hashlib
import secrets
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

from src.database.dynamo.services import DatabaseServices

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _hash_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode()).hexdigest()


class APIKeyRepository:
    _PREFIX = "mcp_"

    def __init__(self):
        self._dbs = DatabaseServices()

    def generate_raw_key(self) -> str:
        return f"{self._PREFIX}{secrets.token_urlsafe(32)}"

    def create_key(self, user_id: str, name: str, scopes: List[str]) -> dict:
        raw_key = self.generate_raw_key()
        key_id = str(uuid.uuid4())
        now = _utcnow_iso()

        record = {
            "key_id": key_id,
            "user_id": user_id,
            "name": name,
            "prefix": raw_key[:12],  # display only — not secret
            "hashed_key": _hash_key(raw_key),
            "scopes": scopes,
            "created_at": now,
            "last_used_at": None,
            "revoked_at": None,
            "is_revoked": False,
        }
        self._dbs.create_api_key(record)
        return {**record, "raw_key": raw_key}  # raw_key added for one-time display

    def list_keys(self, user_id: str) -> List[dict]:
        return self._dbs.list_user_api_keys(user_id)

    def revoke_key(self, key_id: str, user_id: str) -> None:
        key = self._dbs.get_api_key(key_id)
        if not key:
            raise HTTPException(status_code=404, detail="API key not found.")
        if key["user_id"] != user_id:
            raise HTTPException(
                status_code=403, detail="Not authorized to revoke this key."
            )
        if key.get("is_revoked"):
            raise HTTPException(status_code=409, detail="API key already revoked.")
        self._dbs.revoke_api_key(key_id, _utcnow_iso())

    def authenticate_api_key(self, raw_key: str) -> dict:
        """Validates X-API-Key header value. Returns the key record."""
        invalid = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or revoked API key.",
        )
        if not raw_key or not raw_key.startswith(self._PREFIX):
            raise invalid

        key_record = self._dbs.get_api_key_by_hash(_hash_key(raw_key))
        if not key_record:
            raise invalid
        if key_record.get("is_revoked"):
            raise invalid

        self._dbs.update_api_key_last_used(key_record["key_id"], _utcnow_iso())
        return key_record


_repo = APIKeyRepository()


def get_api_key_record(api_key: Optional[str] = Security(_api_key_header)) -> dict:
    """FastAPI dependency — validates X-API-Key and returns key record."""
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-API-Key header missing.",
        )
    return _repo.authenticate_api_key(api_key)
