from pathlib import Path
from langgraph.graph import END as end, START as start, StateGraph
from jinja2 import Environment, FileSystemLoader, StrictUndefined

from src.agent.llm_recall import LLMRecall
from src.models.chatbot import ChatRequest, ChatResponse, ChatbotState



project_root = Path(__file__).resolve().parents[1]
prompt_directory = project_root  # templates live at src/prompts/...

class Chatbot:
    """A small LangGraph workflow that generates one grounded response."""

    def __init__(self, llm_recall=None) -> None:
        self.template_environment = Environment(
            loader=FileSystemLoader(prompt_directory),
            undefined=StrictUndefined,
            autoescape=False,
        )
        self.llm_recall = llm_recall or LLMRecall()
        self.graph = self._build_graph()

    def produce_system_prompt(self) -> str:
        """Load the static system prompt and its safety guardrails."""
        return self.template_environment.get_template(
            "prompts/agent.prompt.system.md"
        ).render()

    def _build_graph(self):
        workflow = StateGraph(ChatbotState)
        workflow.add_node("generate_response", self._generate_response)
        workflow.add_edge(start, "generate_response")
        workflow.add_edge("generate_response", end)
        return workflow.compile()

    def _generate_response(self, state: ChatbotState) -> ChatbotState:
        request = state["request"]
        context = request.context.model_dump()
        response = self.llm_recall.recall(
            system_prompt=self.produce_system_prompt(), 
            user_query=request.user_query, 
            **context)
        return {"response": response}

    def invoke(self, request: ChatRequest) -> ChatResponse:
        """Run the graph for a request and return the generated response."""
        result = self.graph.invoke({"request": request})
        return ChatResponse(user_query=request.user_query, response=result["response"])


if __name__ == "__main__":
    chatbot = Chatbot()
    for i in range(3):
        user_query = input("Enter your query: ")
        request = ChatRequest(
            user_query=user_query,
            context={
                "personality": "friendly",
                "profile": "A curious learner",
                "preferences": "Concise answers",
                "capabilities": "Answering questions",
                "permissions": "Read-only",
                "knowledge": "France is a country in Europe.",
                "tools": "None",
            },
        )
        response = chatbot.invoke(request)
        print(response.response)