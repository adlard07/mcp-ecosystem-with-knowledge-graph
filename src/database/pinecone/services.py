from src.database.pinecone.repositories import PineconeClient
from typing import Any


class PinconeServices:
    def __init__(self):
        self.pinecone_client = PineconeClient()
        
    def create_index(self, index_name: str, dimension: int, metric: str = "cosine") -> None:
        self.pinecone_client.create_index(index_name, dimension, metric)

    def search(self, index_name: str, query_text: str, top_k: int = 5, namespace: str | None = None, fields: list[str] | None = None, rerank_model: str | None = None) -> None:
        self.pinecone_client.search(index_name, query_text, top_k, namespace, fields, rerank_model)

    def upsert_vectors(self, index_name: str, records: list[dict[str, Any]], namespace: str | None = None) -> None:
        self.pinecone_client.upsert_vectors(index_name, records, namespace)

    def fetch_records(self, index_name: str, ids: list[str], namespace: str | None = None) -> None:
        self.pinecone_client.fetch_records(index_name, ids, namespace)

    def delete_records(self, index_name: str, ids: list[str], namespace: str | None = None) -> None:
        self.pinecone_client.delete_records(index_name, ids, namespace)

    