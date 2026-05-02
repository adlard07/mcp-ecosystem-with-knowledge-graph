from typing import Optional

from pydantic import BaseModel


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenData(BaseModel):
    sub: Optional[str] = None  # user_id
    email: Optional[str] = None
    jti: Optional[str] = None
    type: Optional[str] = None  # "access"


class LoginRequest(BaseModel):
    email: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str


class SignupResponse(BaseModel):
    message: str
    username: str
    user_id: str
