import unittest

from src.models.chatbot import ChatContext, ChatResponse
from src.pipeline import ChatbotPipeline


class FakeChatbot:
    def __init__(self) -> None:
        self.requests = []

    def invoke(self, request):
        self.requests.append(request)
        return ChatResponse(user_query=request.user_query, response="Grounded answer")


class TestChatbotPipeline(unittest.TestCase):
    def setUp(self) -> None:
        self.chatbot = FakeChatbot()
        self.pipeline = ChatbotPipeline(
            chatbot=self.chatbot,
            decomposer=lambda query, tools: {
                "intent": "answer the question",
                "questions": [query],
                "tools": [tools],
                "response": "answer directly",
            },
        )

    def test_respond_decomposes_before_invoking_chatbot(self) -> None:
        result = self.pipeline.respond(
            "What is stored?",
            ChatContext(tools="search"),
        )

        self.assertEqual(result.user_query, "What is stored?")
        self.assertEqual(result.response, "Grounded answer")
        self.assertIn("Query decomposition", self.chatbot.requests[0].user_query)
        self.assertEqual(len(self.pipeline.history), 2)

    def test_message_limit_allows_ten_exchanges(self) -> None:
        for number in range(10):
            self.pipeline.respond(f"Question {number}")

        with self.assertRaises(RuntimeError):
            self.pipeline.respond("One too many")


if __name__ == "__main__":
    unittest.main()
