from typing import List, Optional

from pydantic import BaseModel


class CreateAPIKeyRequest(BaseModel):
    name: str
    scopes: List[str] = []


class APIKeyResponse(BaseModel):
    key_id: str
    name: str
    prefix: str  # first 12 chars of raw key — display only
    scopes: List[str]
    created_at: str
    raw_key: str  # shown exactly once at creation


class APIKeyListItem(BaseModel):
    key_id: str
    name: str
    prefix: str
    scopes: List[str]
    created_at: str
    last_used_at: Optional[str] = None
    is_revoked: bool
    revoked_at: Optional[str] = None
