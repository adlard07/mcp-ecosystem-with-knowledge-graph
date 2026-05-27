from src.genai.generate import GenerateResponse
from src.genai.embed import Embedder
from utils.utils import logging


class GenAIServices:
    def __init__(self):
        self.generate_response = GenerateResponse()
        self.embedder = Embedder()

    def generate(self, query: str, model: str) -> dict:
        self.generate_response.generate_response(user_query=query, model=model)
        
    def embed(self, text: str) -> list[float]:
        return self.embedder.embed(text)
    
