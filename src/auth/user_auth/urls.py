import os
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Cookie, Depends, Header, HTTPException, Response, status

from src.auth.user_auth.services import (
    _ACCESS_EXPIRE_MINUTES,
    authenticate_user,
    create_access_token,
    create_refresh_token,
    generate_csrf_token,
    get_current_active_user,
    hash_password,
    revoke_all_sessions,
    revoke_refresh_token,
    rotate_refresh_token,
    validate_csrf_token,
)
from src.database.dynamo.services import DatabaseServices
from src.models.auth import (
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    SignupResponse,
    Token,
)
from src.models.users import CreateUser, User

router = APIRouter(tags=["authentication"], prefix="/auth")
_dbs = DatabaseServices()


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── CSRF ──────────────────────────────────────────────────────────────────────


@router.get("/csrf-token")
def get_csrf_token(response: Response):
    token = generate_csrf_token()
    response.set_cookie(
        key="csrf_token",
        value=token,
        httponly=False,
        samesite="strict",
        secure=os.getenv("ENV") == "production",
    )
    return {"csrf_token": token}


def _require_csrf(
    csrf_token: str = Cookie(default=None),
    x_csrf_token: str = Header(default=None),
):
    if not validate_csrf_token(csrf_token, x_csrf_token):
        raise HTTPException(status_code=403, detail="CSRF token invalid or missing.")


# ── signup ────────────────────────────────────────────────────────────────────


@router.post(
    "/signup",
    response_model=SignupResponse,
    status_code=201,
    dependencies=[Depends(_require_csrf)],
)
async def signup(payload: CreateUser):
    if _dbs.get_user_by_email(payload.email):
        raise HTTPException(status_code=409, detail="Email already registered.")
    if _dbs.get_user_by_username(payload.username):
        raise HTTPException(status_code=409, detail="Username already taken.")

    now = _utcnow_iso()
    user_id = str(uuid.uuid4())
    user = {
        "user_id": user_id,
        "username": payload.username,
        "email": payload.email,
        "hashed_password": hash_password(payload.password),
        "disabled": False,
        "created_at": now,
        "updated_at": now,
    }
    _dbs.create_user(user)
    return SignupResponse(
        message="User created successfully.", username=payload.username, user_id=user_id
    )


# ── login ─────────────────────────────────────────────────────────────────────


@router.post("/login", response_model=Token, dependencies=[Depends(_require_csrf)])
async def login(payload: LoginRequest):
    user = authenticate_user(payload.email, payload.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token, _ = create_access_token(user["user_id"], user["email"])
    refresh_token, _ = create_refresh_token(user["user_id"])

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=_ACCESS_EXPIRE_MINUTES * 60,
    )


# ── refresh ───────────────────────────────────────────────────────────────────


@router.post("/refresh", response_model=Token)
async def refresh(payload: RefreshRequest):
    new_access, new_refresh, user = rotate_refresh_token(payload.refresh_token)
    return Token(
        access_token=new_access,
        refresh_token=new_refresh,
        expires_in=_ACCESS_EXPIRE_MINUTES * 60,
    )


# ── logout ────────────────────────────────────────────────────────────────────


@router.post("/logout", status_code=204, dependencies=[Depends(_require_csrf)])
async def logout(
    payload: LogoutRequest,
    current_user: dict = Depends(get_current_active_user),
):
    revoke_refresh_token(payload.refresh_token)


@router.post("/logout-all", status_code=200, dependencies=[Depends(_require_csrf)])
async def logout_all(current_user: dict = Depends(get_current_active_user)):
    count = revoke_all_sessions(current_user["user_id"])
    return {"revoked_sessions": count}


# ── me ────────────────────────────────────────────────────────────────────────


@router.get("/users/me", response_model=User)
async def read_users_me(current_user: dict = Depends(get_current_active_user)):
    return current_user
