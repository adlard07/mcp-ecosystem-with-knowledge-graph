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
            api_key = api_key or os.getenv("PINECONE_API_KEY")
            if not api_key:
                raise ValueError("PINECONE_API_KEY is required to connect to Pinecone.")
            pinecone_client = Pinecone(api_key=api_key)

        self.index = pinecone_client.Index(
            name=index_name or "",
            host=index_host or "",
        )

    def upsert(
        self,
        vectors: Sequence[Mapping[str, Any]],
        namespace: str = "__default__",
    ) -> Any:
        """Insert or replace vectors in ``namespace``."""
        if not vectors:
            raise ValueError("At least one vector is required.")
        return self.index.upsert(vectors=list(vectors), namespace=namespace)

    def fetch(self, ids: Sequence[str], namespace: str = "__default__") -> Any:
        """Fetch vectors by ID from ``namespace``."""
        if not ids:
            raise ValueError("At least one vector ID is required.")
        return self.index.fetch(ids=list(ids), namespace=namespace)

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
