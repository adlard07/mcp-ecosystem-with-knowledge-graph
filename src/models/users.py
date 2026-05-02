from pydantic import BaseModel, Field

from utils.utils import generate_uuid


class CreateUser(BaseModel):
    user_id: str = Field(default_factory=generate_uuid)
    username: str
    email: str
    password: str


class User(BaseModel):
    user_id: str
    username: str
    email: str
    disabled: bool = False
    created_at: str
    updated_at: str


class UserInDB(User):
    hashed_password: str
