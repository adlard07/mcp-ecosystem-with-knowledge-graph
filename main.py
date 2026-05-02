from fastapi import APIRouter

from src.auth.api_keys.urls import router as api_keys_router
from src.auth.user_auth.urls import router as auth_router

app = APIRouter()

app.include_router(auth_router)
app.include_router(api_keys_router)


@app.get("/", tags=["health"])
def health_check():
    return {"status": "ok"}
