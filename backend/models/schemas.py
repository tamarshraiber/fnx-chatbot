from pydantic import BaseModel, Field

from backend.config import MAX_HISTORY_ITEMS, MAX_MESSAGE_CHARS, MAX_QUESTION_CHARS


class ChatMessage(BaseModel):
    """One message in the conversation history."""
    role: str  # "user" or "assistant"
    content: str = Field(max_length=MAX_MESSAGE_CHARS)


class LLMAnswer(BaseModel):
    """The shape Gemini must reply in."""
    answerable: bool  # False if the chunks do not contain the answer
    answer: str
    source_url: str  # must be one of the URLs we gave the model


class ChatAnswer(BaseModel):
    """The final answer we return to the user."""
    answer: str
    source_url: str | None  # None when the answer is the fixed "not on the website" reply
    found: bool


class ChatRequest(BaseModel):
    """The JSON body the client sends to POST /chat."""
    question: str = Field(min_length=1, max_length=MAX_QUESTION_CHARS)
    history: list[ChatMessage] = Field(default=[], max_length=MAX_HISTORY_ITEMS)
