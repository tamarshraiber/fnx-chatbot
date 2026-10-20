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
# E5 scores sit in a high, narrow range, so this is much higher than the old Gemini cutoff (0.70).
# It was 0.84, but real questions such as "what is the customer service phone number" score only 0.82-0.83
# (their answer is in a table), while some off-topic questions score up to 0.84, so the score alone cannot
# separate them. The cutoff is now 0.80: it only removes clearly unrelated chunks, and the LLM prompt
# (answer only from the chunks, otherwise NOT_FOUND) refuses the rest.
RELEVANCE_THRESHOLD = float(os.getenv("RELEVANCE_THRESHOLD", "0.80"))
# How many chunks we ask the database for.
TOP_K = int(os.getenv("TOP_K", "5"))

# Search asks the database for TOP_K * this many chunks, because identical copies of one page (stored under
# several URLs) are removed afterwards. Without this the copies fill all the slots.
FETCH_MULTIPLIER = int(os.getenv("FETCH_MULTIPLIER", "3"))
# A relevant chunk is often a page heading, while the answer (a phone table, a list) sits in the chunks after it.
# For the best NEIGHBOR_PARENTS chunks we also add the NEIGHBOR_CHUNKS chunks that follow them on the same page.
NEIGHBOR_PARENTS = int(os.getenv("NEIGHBOR_PARENTS", "2"))
NEIGHBOR_CHUNKS = int(os.getenv("NEIGHBOR_CHUNKS", "2"))

# Rerank (step 15). Cohere re-scores the chunks that vector search found, by reading question and chunk together.
# Off by default until the eval set shows it helps. Turn on with RERANK_ENABLED=true.
COHERE_API_KEY = os.getenv("COHERE_API_KEY", "").strip()
RERANK_ENABLED = os.getenv("RERANK_ENABLED", "false").strip().lower() == "true"
RERANK_MODEL = os.getenv("RERANK_MODEL", "rerank-v3.5").strip()
# How many chunks vector search hands to the reranker (we keep TOP_K of them after reranking).
RERANK_FETCH_K = int(os.getenv("RERANK_FETCH_K", "20"))
# Chunks with a rerank score below this are dropped. Placeholder: we set it from the eval set.
RERANK_THRESHOLD = float(os.getenv("RERANK_THRESHOLD", "0.5"))

# Retry (step 11). Total tries per LLM call, and the first wait (it doubles each time).
# Kept short on purpose: we have backup providers, so after one quick retry it is faster to switch than to wait
# (it was 4 tries with 1s, 2s, 4s waits, which could add about 7 seconds to an answer).
RETRY_MAX_ATTEMPTS = int(os.getenv("RETRY_MAX_ATTEMPTS", "2"))
RETRY_BASE_DELAY_SECONDS = float(os.getenv("RETRY_BASE_DELAY_SECONDS", "0.5"))


# Backup LLMs (step 16). Order of use: Gemini first, then Groq, then OpenRouter.
# A provider with no key is skipped. Both backups speak the OpenAI chat format.
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile").strip()
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "").strip()
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "google/gemma-4-31b-it:free").strip()
# An optional second Gemini key, ideally from another Google account: it has its own free quota, so when the first
# key hits its limit (error 429) the second one answers. Empty = not used.
GEMINI_API_KEY_2 = os.getenv("GEMINI_API_KEY_2", "").strip()
LLM_PROVIDER_ORDER = [name.strip() for name in os.getenv("LLM_PROVIDER_ORDER", "gemini,groq,openrouter").split(",") if name.strip()]
# The second key is tried right after the first one, even if LLM_PROVIDER_ORDER (for example in .env) does not list it.
# A provider without a key is skipped anyway.
if "gemini" in LLM_PROVIDER_ORDER and "gemini2" not in LLM_PROVIDER_ORDER:
    LLM_PROVIDER_ORDER.insert(LLM_PROVIDER_ORDER.index("gemini") + 1, "gemini2")
# After a provider fails (quota, overload, network), skip it for this many seconds, then try it again.
LLM_COOLDOWN_SECONDS = float(os.getenv("LLM_COOLDOWN_SECONDS", "60"))
LLM_TIMEOUT_SECONDS = float(os.getenv("LLM_TIMEOUT_SECONDS", "30"))
# Gemini normally answers in about 1 second, but it once hung for 2 minutes. After this many seconds without
# a reply we count it as failed and move on to the next provider.
GEMINI_TIMEOUT_SECONDS = float(os.getenv("GEMINI_TIMEOUT_SECONDS", "10"))


# Answer cache: the same question (after the follow-up rewrite) gets the stored answer at once, with no search and
# no LLM call. This saves the free Gemini quota and makes repeated demo questions instant. Only answers that were
# found are stored. Set ANSWER_CACHE_MAX=0 to turn it off.
ANSWER_CACHE_SECONDS = float(os.getenv("ANSWER_CACHE_SECONDS", "3600"))
ANSWER_CACHE_MAX = int(os.getenv("ANSWER_CACHE_MAX", "200"))

# Safeguards (step 16b). Limits on what POST /chat accepts.
MAX_QUESTION_CHARS = int(os.getenv("MAX_QUESTION_CHARS", "500"))
MAX_HISTORY_ITEMS = int(os.getenv("MAX_HISTORY_ITEMS", "20"))
MAX_MESSAGE_CHARS = int(os.getenv("MAX_MESSAGE_CHARS", "2000"))
# Each client IP may send this many requests per window.
RATE_LIMIT_REQUESTS = int(os.getenv("RATE_LIMIT_REQUESTS", "20"))
RATE_LIMIT_WINDOW_SECONDS = float(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60"))

# CORS (frontend step). Web page addresses allowed to call this API, separated by commas.
CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
    if origin.strip()
]


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
