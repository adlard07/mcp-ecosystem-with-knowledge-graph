import os

from dotenv import load_dotenv
from pinecone import Pinecone, ServerlessSpec

load_dotenv(override=True)


class PineconeInit:
    def __init__(self):
        self.api_key = os.getenv("PINECONE_API_KEY")
        self.pinecone_client = Pinecone(api_key=self.api_key)

    def create_index(self, index_name: str, dimension: int) -> None:
        """Create a new Pinecone index."""
        index_name = "quickstart-py"
        if not self.pinecone_client.has_index(index_name):
            self.pinecone_client.create_index_for_model(
                name=index_name,
                cloud="aws",
                region="ap-south-1",
                embed={
                    "model": "llama-text-embed-v2",
                    "field_map": {"text": "chunk_text"},
                },  # type: ignore
            )
