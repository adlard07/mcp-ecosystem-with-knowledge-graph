import os
from pathlib import Path
from typing import Any
import json

from dotenv import load_dotenv
from jinja2 import Environment, FileSystemLoader, StrictUndefined
from openai import OpenAI

from src.database.supabase_postgres import SupabaseOps

load_dotenv()

project_root = Path(__file__).resolve().parents[1]
prompt_directory = project_root  # templates live at src/prompts/...


class LLMRecall:
    """Answer a user query using the supplied knowledge and user context."""

    def __init__(self, model: str | None = None) -> None:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY is missing from the .env file.")

        self.client = OpenAI(
            api_key=api_key,
            base_url="https://api.groq.com/openai/v1",
        )
        self.decomposer = None
        self.model = model or os.getenv("MODEL_NAME", "openai/gpt-oss-20b")
        self.template_environment = Environment(
            loader=FileSystemLoader(prompt_directory),
            undefined=StrictUndefined,
            autoescape=False,
        )
        self.supabase_conn = SupabaseOps()


    def produce_user_prompt(self, **context: Any) -> str:
        """Render the per-user prompt from the supplied dynamic context."""
        required = {
            "personality",
            "profile",
            "preferences",
            "capabilities",
            "permissions",
            "knowledge",
            "tools",
            "user_query",
        }
        missing = required - context.keys()
        if missing:
            raise ValueError(f"Missing user prompt values: {', '.join(sorted(missing))}")

        return self.template_environment.get_template(
            "prompts/agent.prompt.user_personality.md"
        ).render(**context)
        
    def decompose_query(self, user_query: str, user_personality_context: Any) -> dict[str, Any]:
        """Break a query into intent, questions, user_personality_context, and an answer plan."""
        if self.decomposer:
            decomposition = self.decomposer(user_query, user_personality_context)
        else:
            prompt = self.template_environment.get_template(
                "prompts/agent.prompt.query_decomposition.md"
            ).render(user_query=user_query, user_personality_context=user_personality_context)
            result = self.client.chat.completions.create(
                model=self.model,
                temperature=0,
                messages=[{"role": "user", "content": prompt}],
            )
            decomposition = json.loads(result.choices[0].message.content or "{}")
        # self._validate_decomposition(decomposition)

        return decomposition

    def recall(self, system_prompt, user_query: str, **context: Any) -> str:
        """Return an answer grounded in the rendered user context."""
        if not user_query.strip():
            raise ValueError("user_query cannot be empty.")

        prompt_context = {**context, "user_query": user_query}
        response = self.client.chat.completions.create(
            model=self.model,
            temperature=0.2,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": self.produce_user_prompt(**prompt_context)},
            ],
        )
        return response.choices[0].message.content or ""

    
    def _fetch_user_context(self, user_id: str) -> dict[str, Any]:
        """Fetch the user context from a database or other source."""
        return self.supabase_conn.fetch(table="user_context", filters={"user_id": user_id})


    @staticmethod
    def _validate_decomposition(decomposition: Any) -> None:
        required_keys = {"intent", "questions", "tools", "response"}
        if not isinstance(decomposition, dict) or set(decomposition) != required_keys:
            raise ValueError("Query decomposition must contain intent, questions, tools, and response.")
        if not isinstance(decomposition["questions"], list):
            raise ValueError("Query decomposition questions must be a list.")
        if not isinstance(decomposition["tools"], list):
            raise ValueError("Query decomposition tools must be a list.")
        