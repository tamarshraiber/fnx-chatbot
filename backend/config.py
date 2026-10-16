import os

from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-flash-latest").strip()
SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip()
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "").strip()

EMBEDDING_MODEL =os.getenv("EMBEDDING_MODEL", "gemini-embedding-001").strip()
# Must match the vector column size in Supabase (step 5).
EMBEDDING_DIMENSIONS = int(os.getenv("EMBEDDING_DIMENSIONS", "768"))

# Retrieval (step 7). Chunks with a similarity below the cutoff are treated as not relevant.
# 0.70 fits the first 9 test questions (answerable >= 0.736, unanswerable <= 0.654).
# We recalibrate it later with the eval questions and the full site.
RELEVANCE_THRESHOLD = float(os.getenv("RELEVANCE_THRESHOLD", "0.70"))
# How many chunks we ask the database for.
TOP_K = int(os.getenv("TOP_K", "5"))

# Retry (step 11). Total tries per Gemini call, and the first wait (it doubles each time).
RETRY_MAX_ATTEMPTS = int(os.getenv("RETRY_MAX_ATTEMPTS", "4"))
RETRY_BASE_DELAY_SECONDS = float(os.getenv("RETRY_BASE_DELAY_SECONDS", "1.0"))


def require_gemini_key() -> str:
    """Return the Gemini key, or stop with a clear message if it is missing."""
    if not GEMINI_API_KEY:
        raise RuntimeError(
            "GEMINI_API_KEY is missing. Copy .env.example to .env and paste your key."
        )
    return GEMINI_API_KEY


def require_supabase_settings() -> tuple[str, str]:
    """Return (url, key) for Supabase, or stop with a clear message if one is missing."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise RuntimeError(
            "SUPABASE_URL or SUPABASE_KEY is missing. Add both to your .env file."
        )
    return SUPABASE_URL, SUPABASE_KEY
