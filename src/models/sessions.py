from pydantic import BaseModel, Field

from utils.utils import generate_uuid, get_current_timestamp


class CreateSession(BaseModel):
    session_id: str = Field(default_factory=generate_uuid)
    session: dict
    user_id: str
    server_id: str

    created_at: str = Field(default_factory=get_current_timestamp)
    updated_at: str = Field(default_factory=get_current_timestamp)


class Session(BaseModel):
    session_id: str
    session: dict
    user_id: str
    server_id: str

    created_at: str
    updated_at: str
