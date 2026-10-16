from fastapi import APIRouter, HTTPException

from backend.models.schemas import ChatAnswer, ChatRequest
from backend.services.chat_service import answer_question

router = APIRouter()


@router.post("/chat", response_model=ChatAnswer)
def chat(request: ChatRequest) -> ChatAnswer:
    """Receive a question and the history, and return the bot's answer."""
    if not request.question.strip():
        raise HTTPException(status_code=422, detail="Question must not be empty.")
    try:
        return answer_question(request.question, request.history)
    except Exception as error:
        raise HTTPException(status_code=500, detail="Could not answer the question.") from error
