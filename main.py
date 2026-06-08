from fastapi import APIRouter

from src.models.main import AgentResponse
from src.auth.api_keys.urls import router as api_keys_router
from src.auth.user_auth.urls import router as auth_router
from src.pipeline.preprocess_query import PreprocessQuery

pq = PreprocessQuery()

app = APIRouter()

app.include_router(auth_router)
app.include_router(api_keys_router)


@app.get("/", tags=["health"])
def health_check():
    return {"status": "ok"}


@app.post("/agent_response", tags=["agent"])
def agent_response(state: AgentResponse) -> dict:
    # agent response pipeline
    # query processing
    processes_query = pq.preprocess(state.query)
    
    # rag response 
    
    # tool calling
    
    return {"message": "Agent response received", "state": state.to_dict()}