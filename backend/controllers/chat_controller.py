import itertools
import json
from typing import Iterator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from backend.models.schemas import ChatAnswer, ChatRequest
from backend.services.chat_service import answer_question, stream_answer_question
from backend.services.llm_service import AllProvidersFailed
from backend.services.stats_service import get_public_stats
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


@router.get("/stats")
def stats() -> dict:
    """Public totals for the quality page: pages in the database, last refresh, latest evaluation scores."""
    return get_public_stats()


def _as_lines(events: Iterator[dict]) -> Iterator[str]:
    """One JSON event per line (NDJSON). A failure after the answer has started becomes an error event."""
    try:
        for event in events:
            yield json.dumps(event, ensure_ascii=False) + "\n"
    except AllProvidersFailed:
        yield json.dumps({"type": "error", "status": 503}) + "\n"
    except Exception:
        yield json.dumps({"type": "error", "status": 500}) + "\n"


@router.post("/chat/stream", dependencies=[Depends(check_rate_limit)])
def chat_stream(request: ChatRequest) -> StreamingResponse:
    """Same as /chat, but the answer arrives in pieces while it is being written."""
    if not request.question.strip():
        raise HTTPException(status_code=422, detail="Question must not be empty.")
    events = stream_answer_question(request.question, request.history)
    # Wait for the first event here, so an early failure is still a normal HTTP error (503/500).
    try:
        first = next(events, None)
    except AllProvidersFailed as error:
        raise HTTPException(status_code=503, detail=BUSY_MESSAGE) from error
    except Exception as error:
        raise HTTPException(status_code=500, detail="Could not answer the question.") from error
    rest = itertools.chain([first] if first is not None else [], events)
    return StreamingResponse(
        _as_lines(rest),
        media_type="application/x-ndjson",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
