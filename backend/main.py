from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import CORS_ORIGINS
from backend.controllers.chat_controller import router as chat_router

app = FastAPI(title="Phoenix RAG chatbot")
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)
app.include_router(chat_router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
