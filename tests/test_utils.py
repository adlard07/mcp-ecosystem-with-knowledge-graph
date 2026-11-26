import json
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from src.router import search


def _embedding_response(count: int, dimensions: int = search.EMBEDDING_DIMENSIONS):
    return SimpleNamespace(
        embeddings=[
            SimpleNamespace(values=[0.1] * dimensions) for _ in range(count)
        ]
    )


class TestUploadTools(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.tools_file = Path(self.temp_dir.name) / "tools.json"
        self.tools_file.write_text(
            json.dumps(
                {
                    "tools": [
                        {
                            "tool_name": "gmail_search",
                            "tool_description": "Search email.",
                            "tool_keywords": ["email"],
                            "category": "communication",
                            "use_cases": ["Find an email"],
                            "input_schema": {"query": "string"},
                            "source": "gmail",
                            "access_type": ["read"],
                            "requires_approval": True,
                            "enabled": True,
                        },
                        {
                            "tool_name": "calendar_create",
                            "tool_description": "Create a calendar event.",
                            "input_schema": {"title": "string"},
                            "enabled": False,
                        },
                        {
                            "tool_name": "GMAIL_SEARCH",
                            "tool_description": "Duplicate of gmail_search.",
                        },
                    ]
                }
            ),
            encoding="utf-8",
        )

        self.supabase = MagicMock()
        self.supabase.fetch.return_value = [{"tool_name": "gmail_search"}]
        self.client = MagicMock()
        self.client.models.embed_content.return_value = _embedding_response(2)

        self.env_patcher = patch.dict(
            os.environ, {"GOOGLE_AI_STUDIO_API_KEY": "test-key"}, clear=False
        )
        self.env_patcher.start()
        self.addCleanup(self.env_patcher.stop)
        self.addCleanup(self.temp_dir.cleanup)

        self.file_patcher = patch.object(search, "TOOLS_FILE", self.tools_file)
        self.file_patcher.start()
        self.addCleanup(self.file_patcher.stop)

        self.supabase_patcher = patch.object(search, "SupabaseOps", return_value=self.supabase)
        self.supabase_patcher.start()
        self.addCleanup(self.supabase_patcher.stop)

        self.client_patcher = patch.object(search.genai, "Client", return_value=self.client)
        self.client_patcher.start()
        self.addCleanup(self.client_patcher.stop)

    def test_uploads_only_tools_missing_from_supabase(self) -> None:
        inserted = search.upload_tools()

        self.assertEqual(inserted, 1)
        self.supabase.fetch.assert_called_once_with("tools", columns=["tool_name"])
        self.client.models.embed_content.assert_called_once()
        self.supabase.insert.assert_called_once()

        table, row = self.supabase.insert.call_args.args
        self.assertEqual(table, "tools")
        self.assertEqual(row["tool_name"], "calendar_create")
        self.assertEqual(row["tool_description"], "Create a calendar event.")
        self.assertFalse(row["enabled"])
        self.assertEqual(row["tool_keywords"], "[]")
        self.assertEqual(row["use_cases"], "[]")
        self.assertEqual(row["access_type"], [])
        self.assertFalse(row["requires_approval"])
        self.assertIsNone(row["category"])
        self.assertIsNone(row["source"])
        self.assertEqual(json.loads(row["input_schema"]), {"title": "string"})
        self.assertEqual(
            row["embedding_name"],
            "[" + ",".join(["0.1"] * search.EMBEDDING_DIMENSIONS) + "]",
        )
        self.assertEqual(
            row["embedding_description"],
            "[" + ",".join(["0.1"] * search.EMBEDDING_DIMENSIONS) + "]",
        )
        self.assertIsNone(row["embedding_keywords"])
        self.assertIsNone(row["embedding_category"])
        self.assertIsNone(row["embedding_use_cases"])
        self.assertIsNone(row["embedding_access_type"])

    def test_skips_embedding_when_all_tools_exist(self) -> None:
        self.supabase.fetch.return_value = [
            {"tool_name": "gmail_search"},
            {"tool_name": "CALENDAR_CREATE"},
        ]

        inserted = search.upload_tools()

        self.assertEqual(inserted, 0)
        self.client.models.embed_content.assert_not_called()
        self.supabase.insert.assert_not_called()

    def test_requires_api_key(self) -> None:
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("GOOGLE_AI_STUDIO_API_KEY", None)
            with self.assertRaises(ValueError):
                search.upload_tools()

    def test_rejects_embeddings_with_wrong_dimensions(self) -> None:
        self.client.models.embed_content.return_value = _embedding_response(
            2, dimensions=1024
        )

        with self.assertRaises(ValueError):
            search.upload_tools()

        self.supabase.insert.assert_not_called()


if __name__ == "__main__":
    unittest.main()
