import os

from dotenv import load_dotenv
from fastapi import HTTPException
from google import genai
from mistralai.client import Mistral
from openai import OpenAI

from utils.utils import logging

load_dotenv(override=True)


class GenerateResponse:
    def __init__(self):
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.mistral_api_key = os.getenv("MISTRAL_API_KEY")

        self.pinecone_api_key = os.getenv("PINECONE_API_KEY")
        self.model_name = os.getenv("MODEL_NAME", "mistral-small-latest")

        self.models = {
            # Gemini — free tier (stable)
            "gemini-2.5-pro",
            "gemini-2.5-flash",
            "gemini-2.5-flash-lite",
            # Gemini — free tier (preview, restrictive limits)
            "gemini-3-flash-preview",
            "gemini-3.1-flash-lite-preview",
            "gemini-3.1-flash-live-preview",
            "gemini-3.1-pro-preview",
            # Mistral — all available on free Experiment plan
            "mistral-small-latest",  # Small 4 (open, 24B, hybrid instruct/reasoning/coding)
            "mistral-large-latest",  # Large 3 (open, multimodal)
            "mistral-medium-latest",  # Medium 3.1 (premier, frontier multimodal)
            "magistral-small-latest",  # Small reasoning model
            "magistral-medium-latest",  # Frontier reasoning model
            "ministral-3b-latest",  # 3B edge model
            "ministral-8b-latest",  # 8B edge model
            "ministral-14b-latest",  # 14B multimodal
            "codestral-latest",  # Code completion specialist
            "open-mistral-nemo",  # Nemo 12B (multilingual)
            "devstral-small-latest",  # Code agent model
            # OpenAI
            "gpt-4o-mini",
            "gpt-4o",
            "gpt-4o-nano",
        }

    def generate_gemini_response(self, user_query):
        try:
            client = genai.Client(api_key=self.gemini_api_key)
            response = client.models.generate_content(
                model=self.model_name, contents=user_query
            )
            return response.text
        except Exception as e:
            logging.error(f"Error generating Gemini response: {e}")
            raise HTTPException(
                status_code=500, detail="Error generating Gemini response"
            )

    def generate_openai_response(self, user_query, model="gpt-4o-mini"):
        try:
            client = OpenAI(api_key=self.openai_api_key)
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": user_query}],
            )
            return response.choices[0].message.content
        except Exception as e:
            logging.error(f"Error generating OpenAI response: {e}")
            raise HTTPException(
                status_code=500, detail="Error generating OpenAI response"
            )

    def generate_mistral_response(self, user_query, model="mistral-small-latest"):
        try:
            client = Mistral(api_key=self.mistral_api_key)
            response = client.chat.complete(
                model=model,
                messages=[{"role": "user", "content": user_query}],
            )
            return response.choices[0].message.content
        except Exception as e:
            logging.error(f"Error generating Mistral response: {e}")
            raise HTTPException(
                status_code=500, detail="Error generating Mistral response"
            )

    def generate_response(self, user_query, model=None):
        model = model or self.model_name

        if model not in self.models:
            raise HTTPException(
                status_code=400,
                detail=f"Model '{model}' not supported. Available: {sorted(self.models)}",
            )

        if model.startswith("gemini"):
            return self.generate_gemini_response(user_query)

        elif model.startswith("gpt"):
            return self.generate_openai_response(user_query, model=model)

        elif (
            model.startswith("mistral")
            or model.startswith("magistral")
            or model.startswith("ministral")
            or model.startswith("codestral")
            or model.startswith("open-mistral-nemo")
            or model.startswith("devstral")
        ):
            return self.generate_mistral_response(user_query, model=model)

        else:
            raise HTTPException(
                status_code=400, detail=f"Model '{model}' not supported."
            )


if __name__ == "__main__":
    generator = GenerateResponse()
    user_query = "What is the capital of France?"

    print("\n" + "=" * 60)
    try:
        response = generator.generate_response(user_query)
        print(response)
    except Exception as e:
        print(f"FAIL — {e}")
    print("\n" + "=" * 60)
