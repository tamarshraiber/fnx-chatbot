from pydantic import BaseModel


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
