import unittest

from pydantic import ValidationError

from src.agent.chatbot import Chatbot
from src.models.chatbot import ChatContext, ChatRequest


class FakeRecall:
    def __init__(self) -> None:
        self.calls = []

    def recall(self, user_query: str, **context: object) -> str:
        self.calls.append((user_query, context))
        return f"response for: {user_query}"


class TestChatbot(unittest.TestCase):
    def test_invoke_returns_response_from_llm_recall(self) -> None:
        recall = FakeRecall()
        chatbot = Chatbot(llm_recall=recall)

        result = chatbot.invoke(ChatRequest(user_query="What do I know?"))

        self.assertEqual(result.user_query, "What do I know?")
        self.assertEqual(result.response, "response for: What do I know?")
        self.assertEqual(len(recall.calls), 1)
        self.assertEqual(recall.calls[0][0], "What do I know?")

    def test_invoke_passes_dynamic_context_to_recall(self) -> None:
        recall = FakeRecall()
        chatbot = Chatbot(llm_recall=recall)
        context = ChatContext(
            personality="direct",
            profile="researcher",
            preferences="short answers",
            capabilities="recall",
            permissions="read-only",
            knowledge="A stored note",
            tools="search",
        )

        chatbot.invoke(ChatRequest(user_query="Summarize this", context=context))

        _, received_context = recall.calls[0]
        self.assertEqual(received_context["personality"], "direct")
        self.assertEqual(received_context["knowledge"], "A stored note")
        self.assertEqual(received_context["tools"], "search")

    def test_request_rejects_empty_query(self) -> None:
        with self.assertRaises(ValidationError):
            ChatRequest(user_query="")


if __name__ == "__main__":
    unittest.main()
