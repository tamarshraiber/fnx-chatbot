import os

from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-flash-latest").strip()
SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip()
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "").strip()

# Local model (runs on our own machine, no API key, no quota). Gemini is used only for the answers.
# Documents and questions MUST be embedded by the same model.
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "intfloat/multilingual-e5-base").strip()
# Must match the vector column size in Supabase (step 5).
EMBEDDING_DIMENSIONS = int(os.getenv("EMBEDDING_DIMENSIONS", "768"))

# Retrieval (step 7). Chunks with a similarity below the cutoff are treated as not relevant.
# 0.84 fits the local E5 model on the full site (answerable questions >= 0.86, off-topic questions <= 0.81).
# E5 scores sit in a high, narrow range, so this is much higher than the old Gemini cutoff (0.70).
# We recalibrate it again with the eval questions (step 14/15).
RELEVANCE_THRESHOLD = float(os.getenv("RELEVANCE_THRESHOLD", "0.84"))
# How many chunks we ask the database for.
TOP_K = int(os.getenv("TOP_K", "5"))

# Rerank (step 15). Cohere re-scores the chunks that vector search found, by reading question and chunk together.
# Off by default until the eval set shows it helps. Turn on with RERANK_ENABLED=true.
COHERE_API_KEY = os.getenv("COHERE_API_KEY", "").strip()
RERANK_ENABLED = os.getenv("RERANK_ENABLED", "false").strip().lower() == "true"
RERANK_MODEL = os.getenv("RERANK_MODEL", "rerank-v3.5").strip()
# How many chunks vector search hands to the reranker (we keep TOP_K of them after reranking).
RERANK_FETCH_K = int(os.getenv("RERANK_FETCH_K", "20"))
# Chunks with a rerank score below this are dropped. Placeholder: we set it from the eval set.
RERANK_THRESHOLD = float(os.getenv("RERANK_THRESHOLD", "0.5"))

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
