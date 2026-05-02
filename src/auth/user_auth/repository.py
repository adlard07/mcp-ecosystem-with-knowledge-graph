import hashlib
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

from dotenv import load_dotenv
from fastapi import HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

from src.database.dynamo.services import DatabaseServices
from utils.utils import generate_uuid, get_current_datetime

load_dotenv(override=True)

_ACCESS_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15"))
_REFRESH_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "30"))
_SECRET_KEY = os.getenv("SECRET_KEY", "")
_ALGORITHM = os.getenv("ALGORITHM", "HS256")

if not _SECRET_KEY:
    raise RuntimeError("SECRET_KEY environment variable is not set.")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _utcnow_iso() -> str:
    return _utcnow().isoformat()


class AuthenticationRepository:
    def __init__(self):
        self._pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
        self._dbs = DatabaseServices()
        self.oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

    # ── passwords ─────────────────────────────────────────────────────

    def hash_password(self, plain: str) -> str:
        return self._pwd.hash(plain)

    def verify_password(self, plain: str, hashed: str) -> bool:
        try:
            return self._pwd.verify(plain, hashed)
        except Exception:
            return False

    # ── authenticate ──────────────────────────────────────────────────

    def authenticate_user(self, email: str, password: str) -> Optional[dict]:
        user = self._dbs.get_user_by_email(email)
        if not user:
            return None
        if not self.verify_password(password, user.get("hashed_password", "")):
            return None
        if user.get("disabled"):
            return None
        return user

    # ── access token ──────────────────────────────────────────────────

    def create_access_token(self, user_id: str, email: str) -> Tuple[str, str]:
        """Returns (encoded_jwt, jti)."""
        jti = generate_uuid()
        now = get_current_datetime()
        payload = {
            "sub": user_id,
            "email": email,
            "iat": now,
            "exp": now + timedelta(minutes=_ACCESS_EXPIRE_MINUTES),
            "jti": jti,
            "type": "access",
        }
        token = jwt.encode(payload, _SECRET_KEY, algorithm=_ALGORITHM)
        return token, jti

    # ── refresh token ─────────────────────────────────────────────────

    def _hash_secret(self, secret: str) -> str:
        return hashlib.sha256(secret.encode()).hexdigest()

    def create_refresh_token(self, user_id: str) -> Tuple[str, str]:
        """
        Creates a session in DynamoDB and returns (raw_refresh_token, session_id).
        Token format: <session_id>.<random_secret>
        Only the sha256(secret) is stored.
        """
        session_id = generate_uuid()
        secret = secrets.token_urlsafe(32)
        raw_token = f"{session_id}.{secret}"
        hashed_secret = self._hash_secret(secret)

        now = get_current_datetime()
        expires_at = now + timedelta(days=_REFRESH_EXPIRE_DAYS)
        ttl = int(expires_at.timestamp())

        session = {
            "session_id": session_id,
            "user_id": user_id,
            "hashed_secret": hashed_secret,
            "created_at": now.isoformat(),
            "expires_at": expires_at.isoformat(),
            "ttl": ttl,
        }
        self._dbs.create_session(session)
        return raw_token, session_id

    def verify_refresh_token(self, raw_token: str) -> dict:
        """
        Validates the refresh token and returns the session dict.
        Raises HTTPException on any failure.
        """
        invalid = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token.",
        )
        try:
            session_id, secret = raw_token.split(".", 1)
        except ValueError:
            raise invalid

        session = self._dbs.get_session(session_id)
        if not session:
            raise invalid

        # check expiry (DynamoDB TTL may lag; validate explicitly)
        try:
            expires_at = datetime.fromisoformat(session["expires_at"])
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
        except (KeyError, ValueError):
            raise invalid

        if get_current_datetime() > expires_at:
            self._dbs.delete_session(session_id)
            raise invalid

        if self._hash_secret(secret) != session.get("hashed_secret", ""):
            raise invalid

        return session

    def rotate_refresh_token(self, raw_token: str) -> Tuple[str, str, dict]:
        session = self.verify_refresh_token(raw_token)
        user_id = session["user_id"]

        user = self._dbs.get_user(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found."
            )
        if user.get("disabled"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Account disabled."
            )

        # delete old session before issuing new one (rotation)
        self._dbs.delete_session(session["session_id"])

        access_token, _ = self.create_access_token(user_id, user["email"])
        refresh_token, _ = self.create_refresh_token(user_id)

        return access_token, refresh_token, user

    def revoke_refresh_token(self, raw_token: str) -> None:
        """Logout: delete session. Tolerates already-invalid tokens."""
        try:
            session_id, _ = raw_token.split(".", 1)
        except ValueError:
            return
        self._dbs.delete_session(session_id)

    def revoke_all_sessions(self, user_id: str) -> int:
        return self._dbs.delete_user_sessions(user_id)

    # ── current user dependency ───────────────────────────────────────

    async def get_current_user(self, token: str) -> dict:
        exc = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )
        try:
            payload = jwt.decode(token, _SECRET_KEY, algorithms=[_ALGORITHM])
        except JWTError:
            raise exc

        if payload.get("type") != "access":
            raise exc

        user_id: Optional[str] = payload.get("sub")
        if not user_id:
            raise exc

        user = self._dbs.get_user(user_id)
        if not user:
            raise exc
        return user

    async def get_current_active_user(self, user: dict) -> dict:
        if user.get("disabled"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Account disabled."
            )
        return user

    # ── CSRF ──────────────────────────────────────────────────────────

    def generate_csrf_token(self) -> str:
        return secrets.token_urlsafe(32)

    def validate_csrf_token(self, cookie_token: str, header_token: str) -> bool:
        if not cookie_token or not header_token:
            return False
        return secrets.compare_digest(cookie_token, header_token)
