import os
import time

from sentence_transformers import SentenceTransformer

from utils.utils import logging


class Embedder:
    def __init__(self, model_name: str = "nvidia/llama-nemotron-embed-vl-1b-v2"):
        self.model_name = model_name
        self.model_path = f"./artifacts/{self.model_name}"
        
        self.model: SentenceTransformer | None = None

    def load_model(self) -> None:
        if self.model is not None:
            return
        try:
            start_time = time.perf_counter()
            if os.path.isdir(self.model_path) and os.listdir(self.model_path):
                self.model = SentenceTransformer(
                    self.model_path, trust_remote_code=True
                )
                logging.info(f"Model loaded from local cache: {self.model_path}")
            else:
                self.model = SentenceTransformer(
                    self.model_name, trust_remote_code=True
                )
                os.makedirs(self.model_path, exist_ok=True)
                self.model.save(self.model_path)
                logging.info(f"Model downloaded and cached at: {self.model_path}")

            elapsed = time.perf_counter() - start_time
            logging.info(f"Took {elapsed:.3f} seconds to load model {self.model_name}")
        except Exception as e:
            logging.error(f"Error loading model: {e}")
            raise

    def create_embeddings(self, text: str):
        try:
            self.load_model()

            start_time = time.perf_counter()
            text_embedding = self.model.encode(text)
            elapsed = time.perf_counter() - start_time

            logging.info(f"Took {elapsed:.3f} seconds to create embeddings for text of length {len(text)}")
            return text_embedding
        except Exception as e:
            logging.error(f"Error creating embeddings: {e}")
            raise



if __name__ == "__main__":
    embedder = Embedder()
    text = "This is a sample text to create embeddings."
    embedding = embedder.create_embeddings(text)
    print(embedding)
    print(embedding.shape)