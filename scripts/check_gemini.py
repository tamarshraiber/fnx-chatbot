"""Send one short question to Gemini to prove the key works."""
from google import genai

from backend.config import GEMINI_MODEL, require_gemini_key


def main() -> None:
    client = genai.Client(api_key=require_gemini_key())
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents="Reply with one short sentence in Hebrew: hello.",
    )
    print(f"Model: {GEMINI_MODEL}")
    print(f"Reply: {response.text}")


if __name__ == "__main__":
    main()
