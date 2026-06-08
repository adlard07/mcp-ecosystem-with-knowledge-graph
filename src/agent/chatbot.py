from langgraph.graph import StateGraph, START, END

from src.models.chatbot import OpenChatRequest, ChatState, ChatMessage
from src.genai.generate import GenerateResponse


class ChatAgent:
    def __init__(self):
        self.generate_response = GenerateResponse()
        self.graph = self.build()
        self.system_agent_prompt = self.generate_response._load_prompt("src/prompts/agent_system_prompt.system.md")
        self.user_agent_prompt = self.generate_response._load_prompt("src/prompts/agent_user_prompt.system.md")

    def build(self):
        builder = StateGraph(ChatState)
        builder.add_node("generate", self.generate_response)  # GenerateResponse.__call__ is the node
        builder.add_edge(START, "generate")
        builder.add_edge("generate", END)

        return builder.compile()

    def _generate(self, state: ChatState) -> dict:
        # Adjust this call to match GenerateResponse's actual signature
        response = self.generate_response.generate_response(
            query=state["query"],
            model=state["model"],
            messages=state["chat_state"],
        )
        return {"response": response}

    def invoke(self, request: OpenChatRequest) -> ChatState:
        if not request.messages:
            raise ValueError("At least one message is required")

        latest_message = request.messages[-1]

        state: ChatState = {
            "query": latest_message.content,
            "model": request.model,
            "chat_state": [
                {"role": message.role, "content": message.content}
                for message in request.messages
            ],
            "response": None,
        }

        return self.graph.invoke(state)


if __name__ == "__main__":
    agent = ChatAgent()

    messages: list[ChatMessage] = []

    while True:
        user_input = input("You: ")

        if user_input.lower() in ["exit", "quit"]:
            break

        messages.append(ChatMessage(role="user", content=user_input))

        request = OpenChatRequest(
            user_id="user-123",
            model="gemini-2.5-flash",
            messages=messages,
        )

        result = agent.invoke(request)

        assistant_response = result["response"]
        print(f"AI assistant: {assistant_response}")

        messages.append(
            ChatMessage(role="assistant", content=assistant_response)
        )
    print("Chat ended.")