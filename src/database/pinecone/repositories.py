import os
from uuid import uuid4
from typing import Any
from dotenv import load_dotenv
from pinecone import Pinecone, ServerlessSpec

from utils.utils import logging


load_dotenv(override=True)


class PineconeClient:
    def __init__(self):
        self.api_key = os.getenv("ADELARD_PINECONE_API_KEY")
        self.cloud = os.getenv("ADELARD_PINECONE_ENVIRONMENT")
        self.index_name = os.getenv("ADELARD_PINECONE_INDEX_NAME", "mcp-ecosystem")
        self.region = os.getenv("ADELARD_PINECONE_CLOUD")
        self.model_output_dimentions = os.getenv("ADELARD_MODEL_OUTPUT_DIMENSIONS", "2048")
        
        self.pinecone_client = Pinecone(api_key=self.api_key)
        self._indexes: dict[str, Any] = {}

        self.embed_field = "text"
        self.chat_message_namespace = "chat_messages"
        self.tools_namespace = "tools"
        
        
    def create_index(self, index_name, dimension, metric="cosine", cloud="aws", region=None) -> None:
        try:
            if not self.pinecone_client.has_index(index_name):
                self.pinecone_client.create_index(
                    name=index_name,
                    dimension=dimension,
                    metric=metric,
                    spec=ServerlessSpec(cloud=cloud, region=region),
                )
                logging.info(f"Created Pinecone index '{index_name}' with dimension {dimension} and metric '{metric}'.")
            else:
                logging.info(f"Pinecone index '{index_name}' already exists.")
        except Exception as e:
            logging.error(f"Error creating Pinecone index: {e}")
            raise
        

    def get_index(self, index_name: str):
        try:
            if index_name not in self._indexes:
                self._indexes[index_name] = self.pinecone_client.Index(index_name)
            return self._indexes[index_name]
        except Exception as e:
            logging.error(f"Error getting Pinecone index '{index_name}': {e}")
            raise


    def list_indexes(self) -> list[str]:
        try:
            return [idx["name"] for idx in self.pinecone_client.list_indexes()]
        except Exception as e:
            logging.error(f"Error listing Pinecone indexes: {e}")
            raise


    def delete_index(self, index_name: str) -> None:
        try:
            if self.pinecone_client.has_index(index_name):
                self.pinecone_client.delete_index(index_name)
            self._indexes.pop(index_name, None)
            logging.info(f"Deleted Pinecone index '{index_name}'.")
        except Exception as e:
            logging.error(f"Error deleting Pinecone index '{index_name}': {e}")
            raise


    def describe_stats(self, index_name: str) -> dict[str, Any]:
        try:
            return self.get_index(index_name).describe_index_stats().to_dict()
        except Exception as e:
            logging.error(f"Error describing Pinecone index stats: {e}")
            raise


    # Write records (insert / update)
    
    def upsert_vectors( self, index_name: str, records: list[dict[str, Any]], namespace: str | None = None) -> None:
        try:
            namespace = namespace
            vectors = []
            for rec in records:
                if "id" not in rec:
                    raise ValueError("Every record must include an 'id' field.")
                if "values" not in rec:
                    raise ValueError("Every record must include a 'values' (embedding) field.")
                if self.embed_field not in rec:
                    raise ValueError(f"Every record must include the text field '{self.embed_field}'.")

                metadata = {k: v for k, v in rec.items() if k not in ("id", "values")}
                vectors.append({
                    "id": rec["id"],
                    "values": rec["values"],
                    "metadata": metadata,
                })
            self.get_index(index_name).upsert(vectors=vectors, namespace=namespace)
            logging.info(f"Upserted {len(records)} vectors to Pinecone index '{index_name}' in namespace '{namespace}'.")

        except Exception as e:
            logging.error(f"Error upserting vectors to Pinecone: {e}")
            raise 

            
    # Read records (fetch / query)

    def fetch_records( self, index_name: str, ids: list[str], namespace: str | None = None,) -> dict[str, Any]:
        try:
            namespace = namespace
            response = self.get_index(index_name).fetch(ids=ids, namespace=namespace)
            return response.to_dict()
        except Exception as e:
            logging.error(f"Error fetching records from Pinecone: {e}")
            raise


    def search( self, index_name: str, query_text: str, top_k: int = 5, namespace: str | None = None, fields: list[str] | None = None, rerank_model: str | None = None,) -> dict[str, Any]:
        try:
            namespace = namespace

            query: dict[str, Any] = {
                "inputs": {"text": query_text},
                "top_k": top_k,
            }
            kwargs: dict[str, Any] = {"namespace": namespace, "query": query}
            if fields is not None:
                kwargs["fields"] = fields
            if rerank_model is not None:
                kwargs["rerank"] = {
                    "model": rerank_model,
                    "top_n": top_k,
                    "rank_fields": [self.embed_field],
                }
            return self.get_index(index_name).search(**kwargs).to_dict()
        except Exception as e:
            logging.error(f"Error searching Pinecone index: {e}")
            raise


    # Delete records / namespaces

    def delete_records( self, index_name: str, ids: list[str], namespace: str | None = None,) -> None:
        try:
            namespace = namespace
            self.get_index(index_name).delete(ids=ids, namespace=namespace)
            logging.info(f"Deleted {len(ids)} records from Pinecone index '{index_name}' in namespace '{namespace}'.")
        except Exception as e:
            logging.error(f"Error deleting records from Pinecone: {e}")
            raise


    def delete_namespace( self, index_name: str, namespace: str | None = None,) -> None:
        try:
            namespace = namespace
            self.get_index(index_name).delete(delete_all=True, namespace=namespace)
            logging.info(f"Deleted namespace '{namespace}' from Pinecone index '{index_name}'.")
        except Exception as e:
            logging.error(f"Error deleting namespace from Pinecone: {e}")
            raise    
        
        
if __name__ == "__main__":
    from src.genai.embed import Embedder
    
    pinecone_client = PineconeClient()
    print("Existing indexes:", pinecone_client.list_indexes())
    
    text = "This is a sample text to create embeddings."
    embedder = Embedder()
    embedding = embedder.create_embeddings(text)
    print("Embedding shape:", embedding.shape)
    
    pinecone_client.upsert_vectors(
        index_name=pinecone_client.index_name,
        records=[{
            "id": uuid4().hex,
            "values": embedding.tolist(),
            "text": text,
        }],
        namespace=pinecone_client.chat_message_namespace,
    )