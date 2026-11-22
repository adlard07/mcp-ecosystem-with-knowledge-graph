import os
import unittest
from unittest.mock import MagicMock, patch

from src.agent.llm_recall import LLMRecall


class TestLLMRecall(unittest.TestCase):
    def make_recall(self) -> LLMRecall:
        with patch.dict(os.environ, {"GROQ_API_KEY": "test-key"}, clear=False):
            with patch("src.agent.llm_recall.OpenAI") as openai:
                recall = LLMRecall(model="test-model")
                recall.client = openai.return_value
                return recall

    def test_produce_system_prompt_loads_static_guardrails(self) -> None:
        prompt = self.make_recall().produce_system_prompt()

        self.assertIn("I don't know", prompt)
        self.assertIn("private chain-of-thought", prompt)

    def test_produce_user_prompt_renders_all_context(self) -> None:
        prompt = self.make_recall().produce_user_prompt(
            personality="friendly",
            profile="A researcher",
            preferences="Brief answers",
            capabilities="Recall knowledge",
            permissions="Read-only",
            knowledge="The sky is blue.",
            tools="Search",
            user_query="Why is the sky blue?",
        )

        for value in ("friendly", "A researcher", "Brief answers", "Read-only", "The sky is blue.", "Search", "Why is the sky blue?"):
            self.assertIn(value, prompt)

    def test_produce_user_prompt_rejects_missing_context(self) -> None:
        with self.assertRaises(ValueError):
            self.make_recall().produce_user_prompt(user_query="Hello")

    def test_recall_sends_grounded_prompt_and_temperature(self) -> None:
        recall = self.make_recall()
        message = MagicMock()
        message.content = "The sky is blue because of Rayleigh scattering."
        recall.client.chat.completions.create.return_value.choices = [
            MagicMock(message=message)
        ]

        answer = recall.recall(
            "Why is the sky blue?",
            personality="helpful",
            profile="student",
            preferences="concise",
            capabilities="answer questions",
            permissions="read-only",
            knowledge="The sky is blue.",
            tools="none",
        )

        self.assertEqual(answer, "The sky is blue because of Rayleigh scattering.")
        request = recall.client.chat.completions.create.call_args.kwargs
        self.assertEqual(request["model"], "test-model")
        self.assertEqual(request["temperature"], 0.2)
        self.assertIn("Why is the sky blue?", request["messages"][1]["content"])

    def test_recall_rejects_empty_query(self) -> None:
        with self.assertRaises(ValueError):
            self.make_recall().recall("  ")


if __name__ == "__main__":
    unittest.main()
