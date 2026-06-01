from src.genai.generate import GenerateResponse
from utils.utils import logging


class PreprocessQuery:
    def __init__(self, query):
        self.prompt_path = "src/prompts/process_user_query.system.md"
        self.generate_response = GenerateResponse()
        self.system_prompt = self.generate_response._load_prompt(self.prompt_path)

    # def preprocess(self, query):
        
    #     return processed_query