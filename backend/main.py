from fastapi import FastAPI

from backend.controllers.chat_controller import router as chat_router

app = FastAPI(title="Phoenix RAG chatbot")
app.include_router(chat_router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
