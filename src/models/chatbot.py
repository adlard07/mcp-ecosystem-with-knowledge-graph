from typing import Optional
from typing_extensions import TypedDict
from pydantic import BaseModel, Field

from utils.utils import generate_uuid


class ChatMessage(BaseModel):
    role: str
    content: str


class OpenChatRequest(BaseModel):
    chatbot_id: str = Field(default_factory=generate_uuid)
    user_id: str
    model: Optional[str] = None
    messages: list[ChatMessage] = Field(default_factory=list)


class ChatState(TypedDict, total=False):
    query: str
    response: Optional[str]
    chat_state: list[dict[str, str]]
    model: Optional[str]