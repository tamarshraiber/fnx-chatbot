from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import CORS_ORIGINS
from backend.controllers.chat_controller import router as chat_router
from backend.repositories import vector_repository
from backend.services.embedding_service import embed_question


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load the embedding model now, so the first user question does not wait about 13 seconds for it.
    vector = embed_question("warm up")
    # Open the Supabase connection now too. The first search was about 1s slower than the later ones.
    try:
        vector_repository.search(vector, top_k=1)
    except Exception as error:  # the server must still start if the database is down; questions will show the error
        print(f"Supabase warm-up failed ({type(error).__name__}). Continuing without it.")
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
