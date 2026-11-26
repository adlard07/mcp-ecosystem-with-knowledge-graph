from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Mapping, Sequence

from google import genai
from google.genai import types

from src.database.supabase_postgres import SupabaseOps


class ToolUploader:
    """Embed the local tool catalogue and upload new tools to Supabase."""

    def __init__(self) -> None:
        self.project_root = Path(__file__).resolve().parents[2]
        self.tools_file = self.project_root / "artifacts" / "tools.json"

        self.tools_table = "tools"
        self.embedding_model = "gemini-embedding-001"
        self.embedding_dimensions = 1536
        self.embedding_batch_size = 100

        self.embedding_columns = (
            "embedding_name",
            "embedding_description",
            "embedding_keywords",
            "embedding_category",
            "embedding_use_cases",
            "embedding_access_type",
        )

        self.embedding_model = os.getenv(
            "google_embedding_model",
            self.embedding_model,
        )

        self.api_key = os.getenv("google_ai_studio_api_key")

        self.client = None
        self.supabase_conn = None

    def upload_tools(self) -> int:
        """Embed and insert only new tools into Supabase.

        Existing tool names are compared case-insensitively.
        Returns the number of tools inserted.
        """
        if not self.api_key:
            raise ValueError(
                "google_ai_studio_api_key is missing from the environment."
            )

        tools = self._load_tools(self.tools_file)

        self.supabase_conn = SupabaseOps()

        existing_names = {
            str(row["tool_name"]).strip().casefold()
            for row in self.supabase_conn.fetch(
                self.tools_table,
                columns=["tool_name"],
            )
        }

        new_tools = self._select_new_tools(tools, existing_names)

        if not new_tools:
            return 0

        self.client = genai.Client(api_key=self.api_key)

        embeddings = self._embed_tools(
            model=self.embedding_model,
            tools=new_tools,
        )

        for tool, tool_embeddings in zip(new_tools, embeddings):
            self.supabase_conn.insert(
                self.tools_table,
                self._tool_row(
                    tool,
                    embeddings=tool_embeddings,
                ),
            )

        return len(new_tools)

    def _load_tools(self, path: Path) -> list[dict[str, Any]]:
        """Read the tool catalogue from JSON."""
        if not path.is_file():
            raise FileNotFoundError(
                f"Tool catalogue not found: {path}"
            )

        payload = json.loads(path.read_text(encoding="utf-8"))

        tools = (
            payload.get("tools")
            if isinstance(payload, dict)
            else payload
        )

        if not isinstance(tools, list):
            raise ValueError(
                f"Tool catalogue must contain a list of tools: {path}"
            )

        return tools

    def _select_new_tools(
        self,
        tools: Sequence[Any],
        existing_names: set[str],
    ) -> list[dict[str, Any]]:
        """Remove existing tools and duplicates within the catalogue."""
        seen = set(existing_names)
        selected = []

        for index, tool in enumerate(tools):
            if not isinstance(tool, dict):
                raise ValueError(
                    f"Tool at index {index} must be an object."
                )

            name = str(tool.get("tool_name") or "").strip()

            if not name:
                raise ValueError(
                    f"Tool at index {index} is missing tool_name."
                )

            key = name.casefold()

            if key in seen:
                continue

            seen.add(key)

            selected.append({
                **tool,
                "tool_name": name,
            })

        return selected

    def _embed_tools(
        self,
        *,
        model: str,
        tools: Sequence[dict[str, Any]],
    ) -> list[dict[str, list[float]]]:
        """Generate embeddings for each tool field."""
        texts = []
        slots = []

        for index, tool in enumerate(tools):
            for column, text in self._embedding_texts(tool).items():
                slots.append((index, column))
                texts.append(text)

        vectors = self._embed_texts(
            model=model,
            texts=texts,
        )

        embeddings = [{} for _ in tools]

        for (index, column), vector in zip(slots, vectors):
            embeddings[index][column] = vector

        return embeddings

    def _embedding_texts(
        self,
        tool: Mapping[str, Any],
    ) -> dict[str, str]:
        """Map tool fields to their respective embedding columns."""
        texts = {
            "embedding_name": str(tool.get("tool_name") or ""),
            "embedding_description": str(
                tool.get("tool_description") or ""
            ),
            "embedding_keywords": ", ".join(
                self._string_list(tool.get("tool_keywords"))
            ),
            "embedding_category": str(tool.get("category") or ""),
            "embedding_use_cases": "; ".join(
                self._string_list(tool.get("use_cases"))
            ),
            "embedding_access_type": " ".join(
                self._string_list(tool.get("access_type"))
            ),
        }

        return {
            column: text.strip()
            for column, text in texts.items()
            if text.strip()
        }

    def _embed_texts(
        self,
        *,
        model: str,
        texts: Sequence[str],
    ) -> list[list[float]]:
        """Generate embeddings in batches."""
        if not texts:
            return []

        vectors = []

        for start in range(
            0,
            len(texts),
            self.embedding_batch_size,
        ):
            batch = list(
                texts[start : start + self.embedding_batch_size]
            )

            response = self.client.models.embed_content(
                model=model,
                contents=batch,
                config=types.EmbedContentConfig(
                    task_type="RETRIEVAL_DOCUMENT",
                    output_dimensionality=self.embedding_dimensions,
                ),
            )

            embeddings = response.embeddings or []

            if len(embeddings) != len(batch):
                raise RuntimeError(
                    "Google AI Studio returned a different number "
                    f"of embeddings ({len(embeddings)}) than "
                    f"inputs ({len(batch)})."
                )

            for embedding in embeddings:
                values = [
                    float(value)
                    for value in (embedding.values or [])
                ]

                if len(values) != self.embedding_dimensions:
                    raise ValueError(
                        f"Embedding model {model!r} returned "
                        f"{len(values)} dimensions, expected "
                        f"{self.embedding_dimensions}."
                    )

                vectors.append(values)

        return vectors

    def _tool_row(
        self,
        tool: Mapping[str, Any],
        *,
        embeddings: Mapping[str, Sequence[float]],
    ) -> dict[str, Any]:
        """Convert a tool into a Supabase database row."""
        row = {
            "tool_name": tool["tool_name"],
            "tool_description": str(
                tool.get("tool_description") or ""
            ).strip(),
            "tool_keywords": json.dumps(
                self._string_list(tool.get("tool_keywords"))
            ),
            "category": str(
                tool.get("category") or ""
            ).strip() or None,
            "use_cases": json.dumps(
                self._string_list(tool.get("use_cases"))
            ),
            "input_schema": json.dumps(
                tool.get("input_schema") or {}
            ),
            "source": str(
                tool.get("source") or ""
            ).strip() or None,
            "access_type": self._string_list(
                tool.get("access_type")
            ),
            "requires_approval": bool(
                tool.get("requires_approval", False)
            ),
            "enabled": bool(
                tool.get("enabled", True)
            ),
        }

        for column in self.embedding_columns:
            vector = embeddings.get(column)

            row[column] = (
                self._to_pgvector(vector)
                if vector
                else None
            )

        return row

    def _string_list(self, value: Any) -> list[str]:
        """Normalize a scalar or sequence into a list of strings."""
        if value is None:
            return []

        values = (
            value
            if isinstance(value, (list, tuple))
            else [value]
        )

        return [
            str(item).strip()
            for item in values
            if str(item).strip()
        ]

    def _to_pgvector(self, values: Sequence[float]) -> str:
        """Format a vector for PostgreSQL."""
        return "[" + ",".join(str(value) for value in values) + "]"


if __name__ == "__main__":
    uploader = ToolUploader()

    inserted = uploader.upload_tools()

    print(
        f"Inserted {inserted} new tool(s) into Supabase."
    )