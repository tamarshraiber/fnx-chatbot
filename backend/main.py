from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import CORS_ORIGINS
from backend.controllers.chat_controller import router as chat_router
from backend.services.embedding_service import embed_question


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load the embedding model now, so the first user question does not wait about 13 seconds for it.
    embed_question("warm up")
    yield


app = FastAPI(title="Phoenix RAG chatbot", lifespan=lifespan)
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
