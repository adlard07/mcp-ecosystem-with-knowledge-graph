from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Optional

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from src.agent.chatbot import Chatbot
from src.agent.llm_recall import LLMRecall
from src.models.chatbot import ChatContext, ChatRequest, ChatResponse


class ChatbotPipeline:
    """Decompose queries before sending them to the chatbot, for up to 20 messages."""

    max_messages = 20

    def __init__(
        self,
        chatbot: Optional[Chatbot] = None,
    ) -> None:
        self.llm_recall = LLMRecall()
        self.chatbot = chatbot or Chatbot(self.llm_recall)
        self.history: list[dict[str, str]] = []
        self.template_environment = Environment(
            loader=FileSystemLoader(Path(__file__).resolve().parent),
            undefined=StrictUndefined,
            autoescape=False,
        )

    def respond(
        self,
        user_query: str,
        context: Optional[ChatContext] = None,
    ) -> ChatResponse:
        """Decompose and answer one user query within the message budget."""
        if len(self.history) + 2 > self.max_messages:
            raise RuntimeError("The 20-message conversation limit has been reached.")

        context = context or ChatContext()
        decomposition = self.llm_recall.decompose_query(user_query, context.tools)
        planned_query = (
            f"User query:\n{user_query}\n\n"
            f"Query decomposition:\n{json.dumps(decomposition)}\n\n"
            "Answer the user query using this decomposition as planning context."
        )
        chatbot_response = self.chatbot.invoke(
            ChatRequest(user_query=planned_query, context=context)
        )
        response = ChatResponse(user_query=user_query, response=chatbot_response.response)
        self.history.extend(
            [
                {"role": "user", "content": user_query},
                {"role": "assistant", "content": response.response},
            ]
        )
        return response

    def run(
        self,
        context: Optional[ChatContext] = None,
        input_fn: Callable[[str], str] = input,
        output_fn: Callable[[str], None] = print,
    ) -> None:
        """Run at most 10 user/assistant exchanges (20 messages in total)."""
        while len(self.history) < self.max_messages:
            user_query = input_fn("You: ").strip()
            if not user_query:
                continue
            decomposition = self.llm_recall.decompose_query(user_query, context.tools if context else {})
            if len(decomposition.get("tools")) == 0:
                response = self.respond(user_query, context)
                output_fn(f"Assistant: {response.response}")

    @staticmethod
    def _validate_decomposition(decomposition: Any) -> None:
        required_keys = {"intent", "questions", "tools", "response"}
        if not isinstance(decomposition, dict) or set(decomposition) != required_keys:
            raise ValueError("Query decomposition must contain intent, questions, tools, and response.")
        if not isinstance(decomposition["questions"], list):
            raise ValueError("Query decomposition questions must be a list.")
        if not isinstance(decomposition["tools"], list):
            raise ValueError("Query decomposition tools must be a list.")
