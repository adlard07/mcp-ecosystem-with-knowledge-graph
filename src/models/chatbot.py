"""Data models used by the LangGraph chatbot."""

from typing import Any, TypedDict

from pydantic import BaseModel, Field


class ChatContext(BaseModel):
    """Dynamic context supplied to the assistant for one request."""

    personality: str = "Helpful and concise."
    profile: str = ""
    preferences: str = ""
    capabilities: str = ""
    permissions: str = "None"
    knowledge: Any = ""
    tools: Any = ""


class ChatRequest(BaseModel):
    """Input accepted by the chatbot."""

    user_query: str = Field(min_length=1)
    context: ChatContext = Field(default_factory=ChatContext)


class ChatResponse(BaseModel):
    """Chatbot response returned to the caller."""

    user_query: str
    response: str


class ChatbotState(TypedDict, total=False):
    """State passed between nodes in the chatbot graph."""

    request: ChatRequest
    response: str