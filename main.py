"""FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.auth.urls import router as auth_router


app = FastAPI(title="Personal Knowledge Management System")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    # allow_headers=["Accept", "Authorization", "Content-Type", "Access-Control-Allow-Origin"],
)

@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "ok"} 


app.include_router(auth_router, prefix="/api")


__all__ = ["app"]
