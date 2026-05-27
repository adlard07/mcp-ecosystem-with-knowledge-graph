from langgraph.graph import StateGraph

from src.models.chatbot import OpenChatRequest, ChatState, ChatMessage
from src.genai.generate import GenerateResponse


class ChatAgent:
    def __init__(self):
        self.generate_response = GenerateResponse()
        self.graph = self.build()

    def build(self):
        builder = StateGraph(ChatState)
        builder.add_node()

        return builder.compile()

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
            model="mistral-small-latest",
            messages=messages,
        )

        result = agent.invoke(request)

        assistant_response = result["response"]
        print(f"Bot: {assistant_response}")

        messages.append(ChatMessage(role="assistant", content=assistant_response))
        
        