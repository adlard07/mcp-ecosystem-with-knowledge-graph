from pydantic import BaseModel


class AgentResponse(BaseModel):
    user_query: str
    model_name: str = "gemini-2.5-pro"
    