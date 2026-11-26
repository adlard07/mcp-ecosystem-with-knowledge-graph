from __future__ import annotations

import os
from typing import Any, Mapping, Optional, Sequence

from pinecone import Pinecone


class PinconeOps:
    """Manage vectors in a Pinecone index."""

    def __init__(
        self,
        index_name: Optional[str] = None,
        *,
        index_host: Optional[str] = None,
        api_key: Optional[str] = None,
        pinecone_client: Optional[Any] = None,
    ) -> None:
        if not index_name and not index_host:
            raise ValueError("An index name or index host is required.")

        if pinecone_client is None:
            api_key = api_key or os.getenv("ADELARD_PINECONE_API_KEY")
            if not api_key:
                raise ValueError("PINECONE_API_KEY is required to connect to Pinecone.")
            pinecone_client = Pinecone(api_key=api_key)

        self.index = pinecone_client.Index(
            name=index_name or "",
            host=index_host or "",
        )
        self.embedding_model = os.getenv("EMBEDDING_MODEL")
        self.text_field = os.getenv("PINECONE_EMBEDDING_TEXT_FIELD", "text")


    def upsert(
        self,
        records: Sequence[Mapping[str, Any]],
        namespace: str = "__default__",
    ) -> Any:
        """Insert text records for embedding by Pinecone's integrated index model."""
        if not records:
            raise ValueError("At least one record is required.")

        normalized_records: list[dict[str, Any]] = []
        for record in records:
            normalized = dict(record)
            record_id = normalized.pop("id", normalized.get("_id", None))
            if not record_id:
                raise ValueError("Each record requires an 'id' or '_id'.")
            if not isinstance(normalized.get(self.text_field), str) or not normalized[self.text_field].strip():
                raise ValueError(
                    f"Each record requires non-empty text in {self.text_field!r}."
                )
            if "values" in normalized:
                raise ValueError(
                    "Precomputed 'values' are not supported by an integrated embedding index."
                )
            normalized["_id"] = str(record_id)
            normalized_records.append(normalized)

        return self.index.upsert_records(
            records=normalized_records,
            namespace=namespace,
        )

    def fetch(self, ids: Sequence[str], namespace: str = "__default__") -> Any:
        """Fetch vectors by ID from ``namespace``."""
        if not ids:
            raise ValueError("At least one vector ID is required.")
        return self.index.fetch(ids=list(ids), namespace=namespace)

    def search_documents(
        self,
        query_text: str,
        *,
        namespace: str = "__default__",
        top_k: int = 5,
        text_field: Optional[str] = None,
        include_fields: Optional[Sequence[str]] = None,
        filter: Optional[Mapping[str, Any]] = None,
    ) -> list[dict[str, Any]]:
        """Semantic search over a document-schema index (Documents API).

        ``text_field`` must declare ``embed`` in the index schema; Pinecone
        embeds ``query_text`` with that field's model, so no local embedding is
        required. Returns ``{"id", "score", "fields"}`` dicts, highest first.
        """
        if not isinstance(query_text, str) or not query_text.strip():
            raise ValueError("query_text must be a non-empty string.")
        if top_k <= 0:
            raise ValueError("top_k must be positive.")

        field = text_field or self.text_field
        response = self.index.documents.search(
            namespace=namespace,
            top_k=top_k,
            score_by=[{"type": "embed", "fields": [field], "query": query_text}],
            include_fields=list(include_fields) if include_fields else None,
            filter=dict(filter) if filter else None,
        )

        hits: list[dict[str, Any]] = []
        for match in response.matches:
            raw = match.to_dict() if hasattr(match, "to_dict") else {}
            nested = raw.get("fields") if isinstance(raw, dict) else None
            if isinstance(nested, dict):
                fields = nested
            else:
                fields = {
                    key: value
                    for key, value in raw.items()
                    if key not in {"id", "_id", "score"}
                }
            hits.append({"id": match.id, "score": match.score, "fields": fields})
        return hits

    def update(
        self,
        vector_id: str,
        *,
        namespace: str = "__default__",
        values: Optional[Sequence[float]] = None,
        sparse_values: Optional[Mapping[str, Sequence[float]]] = None,
        set_metadata: Optional[Mapping[str, Any]] = None,
    ) -> Any:
        """Update a vector's values and/or metadata by ID."""
        if not vector_id:
            raise ValueError("A vector ID is required.")
        if values is None and sparse_values is None and set_metadata is None:
            raise ValueError("Values, sparse values, or metadata is required for update.")

        return self.index.update(
            id=vector_id,
            namespace=namespace,
            values=list(values) if values is not None else None,
            sparse_values=dict(sparse_values) if sparse_values is not None else None,
            set_metadata=dict(set_metadata) if set_metadata is not None else None,
        )

    def delete(
        self,
        *,
        namespace: str = "__default__",
        ids: Optional[Sequence[str]] = None,
        filter: Optional[Mapping[str, Any]] = None,
        delete_all: bool = False,
    ) -> Any:
        """Delete vectors by ID, metadata filter, or an entire namespace."""
        requested_deletions = sum(
            option is not None for option in (ids, filter)
        ) + bool(delete_all)
        if requested_deletions != 1:
            raise ValueError("Specify exactly one of ids, filter, or delete_all.")
        if ids is not None and not ids:
            raise ValueError("At least one vector ID is required.")

        return self.index.delete(
            namespace=namespace,
            ids=list(ids) if ids is not None else None,
            filter=dict(filter) if filter is not None else None,
            delete_all=delete_all,
        )
