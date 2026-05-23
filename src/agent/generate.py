import os

from dotenv import load_dotenv
from fastapi import HTTPException
from google import genai
from mistralai.client import Mistral
from openai import OpenAI

from src.models.chatbot import ChatState
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
            "gemini-2.5-pro",
            "gemini-2.5-flash",
            "gemini-2.5-flash-lite",
            "gemini-3-flash-preview",
            "gemini-3.1-flash-lite-preview",
            "gemini-3.1-flash-live-preview",
            "gemini-3.1-pro-preview",

            "mistral-small-latest",
            "mistral-large-latest",
            "mistral-medium-latest",
            "magistral-small-latest",
            "magistral-medium-latest",
            "ministral-3b-latest",
            "ministral-8b-latest",
            "ministral-14b-latest",
            "codestral-latest",
            "open-mistral-nemo",
            "devstral-small-latest",

            "gpt-4o-mini",
            "gpt-4o",
            "gpt-4o-nano",
        }

        self.system_prompt = self._load_prompt("prompts/agent_system_prompt.system.md")
        self.user_prompt = self._load_prompt("prompts/agent_user_prompt.user.md")


    def _load_prompt(self, path: str) -> str:
        try:
            with open(path, "r", encoding="utf-8") as file:
                return file.read()
        except FileNotFoundError:
            logging.error(f"Prompt file not found: {path}")
            raise HTTPException(
                status_code=500,
                detail=f"Prompt file not found: {path}",
            )


    def __call__(self, state: ChatState) -> dict:
        query = state.get("query")
        model = state.get("model")

        if not query:
            raise HTTPException(status_code=400, detail="Query is required")

        chat_state = state.get("chat_state", [])

        response = self.generate_response(
            user_query=query,
            model=model,
            messages=chat_state,
        )

        updated_chat_state = [
            *chat_state,
            {"role": "assistant", "content": response},
        ]

        return {
            "response": response,
            "chat_state": updated_chat_state,
        }


    def build_messages(
        self,
        user_query: str,
        messages: list[dict[str, str]] | None = None,
    ) -> list[dict[str, str]]:
        messages = messages or []

        formatted_user_prompt = self.user_prompt.format(
            user_query=user_query,
        )

        conversation_without_latest_user = messages[:-1]

        return [
            {"role": "system", "content": self.system_prompt},
            *conversation_without_latest_user,
            {"role": "user", "content": formatted_user_prompt},
        ]


    def generate_gemini_response(
        self,
        messages: list[dict[str, str]],
        model: str,
    ):
        try:
            client = genai.Client(api_key=self.gemini_api_key)

            system_instruction = messages[0]["content"]
            conversation = messages[1:]

            contents = []
            for message in conversation:
                role = "model" if message["role"] == "assistant" else "user"
                contents.append(
                    {
                        "role": role,
                        "parts": [{"text": message["content"]}],
                    }
                )

            response = client.models.generate_content(
                model=model,
                contents=contents,
                config={
                    "system_instruction": system_instruction,
                },
            )

            return response.text

        except Exception as e:
            logging.error(f"Error generating Gemini response: {e}")
            raise HTTPException(
                status_code=500,
                detail="Error generating Gemini response",
            )


    def generate_openai_response(
        self,
        messages: list[dict[str, str]],
        model: str = "gpt-4o-mini",
    ):
        try:
            client = OpenAI(api_key=self.openai_api_key)
            response = client.chat.completions.create(
                model=model,
                messages=messages,
            )
            return response.choices[0].message.content
        except Exception as e:
            logging.error(f"Error generating OpenAI response: {e}")
            raise HTTPException(
                status_code=500,
                detail="Error generating OpenAI response",
            )


    def generate_mistral_response(
        self,
        messages: list[dict[str, str]],
        model: str = "mistral-small-latest",
    ):
        try:
            client = Mistral(api_key=self.mistral_api_key)
            response = client.chat.complete(
                model=model,
                messages=messages,
            )
            return response.choices[0].message.content
        except Exception as e:
            logging.error(f"Error generating Mistral response: {e}")
            raise HTTPException(
                status_code=500,
                detail="Error generating Mistral response",
            )


    def generate_response(
        self,
        user_query: str,
        model: str | None = None,
        messages: list[dict[str, str]] | None = None,
    ):
        model = model or self.model_name

        if model not in self.models:
            raise HTTPException(
                status_code=400,
                detail=f"Model '{model}' not supported. Available: {sorted(self.models)}",
            )

        provider_messages = self.build_messages(
            user_query=user_query,
            messages=messages,
        )

        if model.startswith("gemini"):
            return self.generate_gemini_response(provider_messages, model=model)

        if model.startswith("gpt"):
            return self.generate_openai_response(provider_messages, model=model)

        if (
            model.startswith("mistral")
            or model.startswith("magistral")
            or model.startswith("ministral")
            or model.startswith("codestral")
            or model.startswith("open-mistral-nemo")
            or model.startswith("devstral")
        ):
            return self.generate_mistral_response(provider_messages, model=model)

        raise HTTPException(
            status_code=400,
            detail=f"Model '{model}' not supported.",
        )