from fastapi import APIRouter, Depends, HTTPException

from backend.models.schemas import ChatAnswer, ChatRequest
from backend.services.chat_service import answer_question
from backend.services.llm_service import AllProvidersFailed
from backend.utils.rate_limit import check_rate_limit

router = APIRouter()

BUSY_MESSAGE = "השירות עמוס כרגע, נסו שוב בעוד כמה דקות."


@router.post("/chat", response_model=ChatAnswer, dependencies=[Depends(check_rate_limit)])
def chat(request: ChatRequest) -> ChatAnswer:
    """Receive a question and the history, and return the bot's answer."""
    if not request.question.strip():
        raise HTTPException(status_code=422, detail="Question must not be empty.")
    try:
        return answer_question(request.question, request.history)
    except AllProvidersFailed as error:
        raise HTTPException(status_code=503, detail=BUSY_MESSAGE) from error
    except Exception as error:
        raise HTTPException(status_code=500, detail="Could not answer the question.") from error
