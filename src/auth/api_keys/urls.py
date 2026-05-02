from typing import List

from fastapi import APIRouter, Depends, HTTPException

from src.auth.api_keys.services import create_api_key, list_api_keys, revoke_api_key
from src.auth.user_auth.services import get_current_active_user
from src.models.api_keys import APIKeyListItem, APIKeyResponse, CreateAPIKeyRequest

router = APIRouter(tags=["api-keys"], prefix="/api-keys")


@router.post("", response_model=APIKeyResponse, status_code=201)
async def create_key(
    payload: CreateAPIKeyRequest,
    current_user: dict = Depends(get_current_active_user),
):
    record = create_api_key(current_user["user_id"], payload.name, payload.scopes)
    return APIKeyResponse(
        key_id=record["key_id"],
        name=record["name"],
        prefix=record["prefix"],
        scopes=record["scopes"],
        created_at=record["created_at"],
        raw_key=record["raw_key"],
    )


@router.get("", response_model=List[APIKeyListItem])
async def list_keys(current_user: dict = Depends(get_current_active_user)):
    keys = list_api_keys(current_user["user_id"])
    return [
        APIKeyListItem(
            key_id=k["key_id"],
            name=k["name"],
            prefix=k["prefix"],
            scopes=k.get("scopes", []),
            created_at=k["created_at"],
            last_used_at=k.get("last_used_at"),
            is_revoked=k.get("is_revoked", False),
            revoked_at=k.get("revoked_at"),
        )
        for k in keys
    ]


@router.delete("/{key_id}", status_code=204)
async def revoke_key(
    key_id: str,
    current_user: dict = Depends(get_current_active_user),
):
    revoke_api_key(key_id, current_user["user_id"])
