from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional
from uuid import uuid4

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from src.agent.chatbot import Chatbot
from src.agent.llm_recall import LLMRecall
from src.database.pinecone_vector import PinconeOps
from src.database.supabase_postgres import SupabaseOps
from src.models.chatbot import ChatContext, ChatRequest, ChatResponse


class ChatbotPipeline:
    """Run a chat session and persist its messages in Postgres and Pinecone."""

    max_messages = 20
    chats_table = "chats"
    messages_table = "messages"

    def __init__(
        self,
        chatbot: Optional[Chatbot] = None,
        *,
        postgres: Optional[SupabaseOps] = None,
        vector_store: Optional[PinconeOps] = None,
        tools_store: Optional[PinconeOps] = None,
        embedding_model: str = "llama-text-embed-v2",
        decomposer: Optional[Callable[[str, Any], dict[str, Any]]] = None,
        input_fn: Callable[[str], str] = input,
        output_fn: Callable[[str], None] = print,
    ) -> None:
        self.llm_recall = LLMRecall()
        self.chatbot = chatbot
        self.postgres = postgres
        self.vector_store = vector_store
        self.tools_store = tools_store
        self.embedding_model = embedding_model
        self.decomposer = decomposer
        self.input_fn = input_fn
        self.output_fn = output_fn
        self.history: list[dict[str, str]] = []
        self.template_environment = Environment(
            loader=FileSystemLoader(Path(__file__).resolve().parent),
            undefined=StrictUndefined,
            autoescape=False,
        )

    def chat(
        self,
        user_id: str,
        chat_id: Optional[str] = None,
        context: Optional[ChatContext] = None,
    ) -> str:
        """Run up to ten user/assistant exchanges and return the chat ID.

        Postgres is the source of truth for the conversation. ``user_id`` owns
        the chat, and is required to create or resume it. Pinecone stores an
        embedding for each message, keyed by its Postgres message ID, so records
        can be filtered by both ``chat_id`` and ``message_id`` during retrieval.
        Enter ``exit`` or ``quit`` to end the interactive session.
        """
        postgres = self._postgres()
        vector_store = self._vector_store()
        chatbot = self._chatbot()
        context = context or ChatContext()
        user_id = str(user_id).strip()
        if not user_id:
            raise ValueError("user_id is required to create or resume a chat.")

        if chat_id is None:
            chat_id = str(uuid4())
            now = self._timestamp()
            postgres.insert(
                self.chats_table,
                {
                    "chat_id": chat_id,
                    "user_id": user_id,
                    "created_at": now,
                    "updated_at": now,
                },
            )
        else:
            chat_id = str(chat_id)
            if not postgres.fetch(
                self.chats_table, {"chat_id": chat_id, "user_id": user_id}
            ):
                raise ValueError(f"Chat {chat_id!r} does not exist for this user.")

        message_count = len(postgres.fetch(self.messages_table, {"chat_id": chat_id}))
        while message_count + 2 <= self.max_messages:
            user_query = self.input_fn("You: ").strip()
            if user_query.lower() in {"exit", "quit"}:
                break
            if not user_query:
                continue

            self._store_message(
                postgres=postgres,
                vector_store=vector_store,
                user_id=user_id,
                chat_id=chat_id,
                role="user",
                content=user_query,
            )
            self.history.append({"role": "user", "content": user_query})

            # response = chatbot.invoke(ChatRequest(user_query=user_query, context=context))
            response = self.respond(user_query=user_query, user_id=user_id)
            self._store_message(
                postgres=postgres,
                vector_store=vector_store,
                user_id=user_id,
                chat_id=chat_id,
                role="assistant",
                content=response.response,
            )
            self.history.append({"role": "assistant", "content": response.response})
            self.output_fn(f"Assistant: {response.response}")
            message_count += 2

        return chat_id

    def respond(self, user_query: str, user_id: str) -> ChatResponse:
        """Generate one response while retaining the original query as the ID."""
        if len(self.history) >= self.max_messages:
            raise RuntimeError("The conversation has reached its 20-message limit.")

        context = self.llm_recall._fetch_user_context(user_id=user_id)
        # print(f"\n==================\n{context}\n==================\n")
        decomposition = (
            self.decomposer(user_query, context)
            if self.decomposer
            else self.llm_recall.decompose_query(user_query, context)
        )
        enriched_query = f"Query decomposition:\n{json.dumps(decomposition)}\n\nUser query: {user_query}"
        print(f"\n==================\n{enriched_query}\n==================\n")
        
        tools = self._search_tools(user_query)
        if tools:
            enriched_query += f"\n\nRelevant tools:\n{json.dumps(tools)}"

        response = self._chatbot().invoke(
            ChatRequest(user_query=enriched_query)
        )
        self.history.extend(
            [
                {"role": "user", "content": user_query},
                {"role": "assistant", "content": response.response},
            ]
        )
        return ChatResponse(user_query=user_query, response=response.response)

    def _store_message(
        self,
        *,
        postgres: SupabaseOps,
        vector_store: PinconeOps,
        user_id: str,
        chat_id: str,
        role: str,
        content: str,
    ) -> str:
        """Persist one message and compensate if Postgres rejects its row."""
        message_id = str(uuid4())
        created_at = self._timestamp()
        vector_store.upsert(
            [{
                "id": message_id,
                "text": content,
                "chat_id": chat_id,
                "message_id": message_id,
                "role": role,
                "created_at": created_at,
                "embedding_model": self.embedding_model,
            }],
            namespace=self._namespace(),
        )

        try:
            postgres.insert(
                self.messages_table,
                {
                    "message_id": message_id,
                    "chat_id": chat_id,
                    "role": role,
                    "content": content,
                    "metadata": json.dumps({"embedding_model": self.embedding_model}),
                    "created_at": created_at,
                },
            )
            postgres.update(
                self.chats_table,
                {"updated_at": created_at},
                {"chat_id": chat_id, "user_id": user_id},
            )
        except Exception:
            # The data stores cannot share a transaction. Avoid an orphan vector
            # when the canonical Postgres write fails.
            vector_store.delete(ids=[message_id], namespace=self._namespace())
            raise

        return message_id

    def _postgres(self) -> SupabaseOps:
        if self.postgres is None:
            self.postgres = SupabaseOps()
        return self.postgres

    def _vector_store(self) -> PinconeOps:
        if self.vector_store is None:
            index_name = os.getenv("PINECONE_INDEX_NAME") or os.getenv("ADELARD_PINECONE_INDEX_NAME")
            index_host = os.getenv("PINECONE_INDEX_HOST") or os.getenv("ADELARD_PINECONE_HOST")
            self.vector_store = PinconeOps(index_name=index_name, index_host=index_host)
        return self.vector_store

    def _search_tools(
        self, user_query: str, *, top_k: Optional[int] = None
    ) -> list[dict[str, Any]]:
        """Return the tools that best match ``user_query`` semantically.

        Runs against the tools document index before query decomposition, using
        the query text directly (Pinecone embeds it with the index's own model).
        An empty catalogue yields an empty list, leaving the caller's tool
        context untouched.
        """
        query = (user_query or "").strip()
        if not query:
            return []

        hits = self._tools_store().search_documents(
            query,
            namespace=self._tools_namespace(),
            top_k=top_k or int(os.getenv("PINECONE_TOOLS_TOP_K", "5")),
            text_field=os.getenv("PINECONE_TOOLS_TEXT_FIELD", "chunk_text"),
            include_fields=("title", "chunk_text", "input_schema"),
        )

        tools: list[dict[str, Any]] = []
        for hit in hits:
            fields = hit.get("fields") or {}
            tool: dict[str, Any] = {
                "tool_id": hit["id"],
                "tool_name": fields.get("title") or hit["id"],
                "tool_description": fields.get("chunk_text") or "",
                "score": round(float(hit.get("score") or 0.0), 4),
            }
            if fields.get("input_schema"):
                tool["input_schema"] = fields["input_schema"]
            tools.append(tool)
        return tools

    def _tools_store(self) -> PinconeOps:
        if self.tools_store is None:
            index_name = os.getenv("PINECONE_TOOLS_INDEX_NAME", "tools")
            index_host = os.getenv("PINECONE_TOOLS_INDEX_HOST", "")
            self.tools_store = PinconeOps(index_name=index_name, index_host=index_host)
        return self.tools_store

    def _chatbot(self) -> Chatbot:
        if self.chatbot is None:
            self.chatbot = Chatbot()
        return self.chatbot


    @staticmethod
    def _timestamp() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _namespace() -> str:
        return os.getenv("PINECONE_CHAT_NAMESPACE", "chat-messages")

    @staticmethod
    def _tools_namespace() -> str:
        return os.getenv("PINECONE_TOOLS_NAMESPACE", "__default__")



if __name__ == "__main__":
    pipeline = ChatbotPipeline()
    chat_id = pipeline.chat(user_id='bdea8589-6075-49e3-a340-73f437fd65a3')
    print(f"Chat session ended. Chat ID: {chat_id}")
