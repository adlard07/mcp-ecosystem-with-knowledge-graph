import unittest
from types import SimpleNamespace

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


class FakePostgres:
    def __init__(self) -> None:
        self.rows = {"chats": [], "messages": []}

    def insert(self, table, values):
        row = dict(values)
        self.rows[table].append(row)
        return row

    def fetch(self, table, filters=None):
        return [
            row for row in self.rows[table]
            if not filters or all(row[key] == value for key, value in filters.items())
        ]

    def update(self, table, values, filters):
        matches = self.fetch(table, filters)
        for row in matches:
            row.update(values)
        return len(matches)


class FakeVectorStore:
    def __init__(self) -> None:
        self.vectors = []

    def upsert(self, vectors, namespace):
        self.vectors.extend(vectors)

    def delete(self, **_kwargs):
        return None


class TestPersistentChat(unittest.TestCase):
    def test_chat_persists_postgres_rows_and_pinecone_metadata(self) -> None:
        postgres = FakePostgres()
        vector_store = FakeVectorStore()
        messages = iter(["What is stored?", "exit"])
        pipeline = ChatbotPipeline(
            chatbot=FakeChatbot(),
            postgres=postgres,
            vector_store=vector_store,
            input_fn=lambda _prompt: next(messages),
            output_fn=lambda _message: None,
        )

        user_id = "b2b412a1-2fc9-4bb9-887a-59521b401080"
        chat_id = pipeline.chat(user_id)

        self.assertEqual(postgres.rows["chats"][0]["chat_id"], chat_id)
        self.assertEqual(postgres.rows["chats"][0]["user_id"], user_id)
        self.assertEqual(len(postgres.rows["messages"]), 2)
        self.assertEqual(len(vector_store.vectors), 2)
        for vector, message in zip(vector_store.vectors, postgres.rows["messages"]):
            self.assertEqual(vector["id"], message["message_id"])
            self.assertEqual(vector["chat_id"], chat_id)
            self.assertEqual(vector["message_id"], message["message_id"])

        with self.assertRaisesRegex(ValueError, "does not exist for this user"):
            pipeline.chat("973e32ca-6637-48e6-a0bc-41f8df06ec83", chat_id)


if __name__ == "__main__":
    unittest.main()
