# STEP.md - Build steps for the Phoenix (fnx.co.il) Hebrew RAG chatbot

Status: DONE / NEXT / TODO

## Part A - Terminal bot on ~5 pages
| # | Step | Status | Notes |
|---|---|---|---|
| 1 | Setup | DONE | requirements.txt, .env.example, backend/config.py, scripts/check_gemini.py. Model: gemini-2.5-flash. Committed. |
| 2 | Scraper | DONE | backend/ingestion/config.py, scraper.py. 5 test pages saved to data/raw/. |
| 3 | Chunker | DONE | backend/ingestion/chunker.py, chunk settings in config.py. 47 chunks from 5 pages saved to data/chunks/chunks.json. Removes cookie banner, images, link URLs and shared footer. |
| 4 | Embeddings | DONE | backend/services/embedding_service.py (768 dims), scripts/check_embeddings.py. |
| 5 | Supabase table + repository | DONE | supabase/schema.sql, vector_repository.py, scripts/check_supabase.py. |
| 6 | embed_upload | DONE | backend/ingestion/embed_upload.py. Embeds chunks.json, deletes old rows per page, upserts by chunk_id. Run: python -m backend.ingestion.embed_upload |
| 7 | Retrieval | DONE | backend/services/retrieval_service.py, scripts/check_retrieval.py, RELEVANCE_THRESHOLD (0.70, fits 9 test questions) and TOP_K in config.py. Recalibrate with the full site and eval set. |
| 8 | Generation | DONE | backend/models/schemas.py, backend/services/generation_service.py, scripts/check_generation.py. Answer only from chunks. Cited URL must be one of the retrieved URLs, otherwise "not on the website". |
| 9 | Chat service with history | DONE | backend/services/chat_service.py, scripts/chat_terminal.py, ChatMessage in schemas.py. Follow-up questions are rewritten into standalone questions (last 6 messages). Run: python -m scripts.chat_terminal |

## Part B - Backend API
| # | Step | Status | Notes |
|---|---|---|---|
| 10 | FastAPI /chat | DONE | backend/main.py, backend/controllers/chat_controller.py, ChatRequest in schemas.py. POST /chat (question + history), GET /health. Run: uvicorn backend.main:app --reload (docs at /docs). CORS comes in the frontend step. |
| 11 | Retry with backoff on 429/503 | DONE | backend/utils/retry.py, scripts/check_retry.py, RETRY_* in config.py. Used for the rewrite, answer and question-embedding calls (not embed_chunks). Test: python -m scripts.check_retry |

## Part C - Full data
| # | Step | Status | Notes |
|---|---|---|---|
| 12 | Full crawl from the sitemap | DONE | scraper.py picks pages from the sitemap (INCLUDE_SECTIONS in config.py, 1,145 pages). Run: python -m backend.ingestion.scraper --list / --limit N / --all (--all resumes). About 1,133 pages saved; a few failed because the NetFree filter blocks them (retry from another connection). |
| 13 | One-command incremental pipeline | DONE (not run on real data yet) | backend/ingestion/run.py, state.py, scripts/check_pipeline.py. Run: python -m backend.ingestion.run --dry-run / (no flag) / --full / --max-pages N. Embeds page by page, resumable after a Gemini quota stop. Removed pages are deleted only if the site says 404/410. Offline test: python -m scripts.check_pipeline |
| 13b | Local embeddings | DONE | Embeddings run locally with intfloat/multilingual-e5-base (backend/services/embedding_service.py, EMBEDDING_MODEL in config.py). Gemini only rewrites and answers. Table was emptied once and reloaded: 1,064 pages in Supabase (the rest are NetFree-blocked or empty). RELEVANCE_THRESHOLD is now 0.84 (answerable >= 0.858, off-topic <= 0.805; margin is small, recheck in step 14/15). Tests: python -m scripts.check_embeddings, scripts.check_local_quality, scripts.check_retrieval |

## Part D - Quality
| # | Step | Status | Notes |
|---|---|---|---|
| 14 | Eval set (~30 questions) | DONE | data/eval/eval_set.json (20 answerable with expected pages, 10 unanswerable: 5 clearly off-topic, 5 "hard" insurance/finance-related), scripts/eval_retrieval.py (retrieval only, no Gemini). Run: python -m scripts.eval_retrieval. Baseline at cutoff 0.84: answerable kept 20/20, expected page in top 5 20/20, unanswerable rejected 5/10 (all 5 hard ones leak, scores 0.857-0.908). Cutoff alone cannot separate them; this is the job of step 15 (rerank / hybrid) and the "not on the website" rule in generation. |
| 15 | Tune retrieval | IN PROGRESS | 15a+15b done: backend/services/rerank_service.py (Cohere rerank-v3.5), switchable in retrieval_service.py (RERANK_ENABLED, default false; falls back to vector search if Cohere fails), RERANK_* in config.py, scripts/eval_retrieval.py compares vector vs rerank (--cached / --no-rerank). Eval result: vector best 25/30 at 0.84; rerank best 27/30 at cutoff 0.70-0.75 (rejects 4 of the 5 hard questions, but drops 2 answerable ones). Small gain, small eval set. Not enabled yet; 15c hybrid search not started. |
| 16 | Backup LLM + safeguards | DONE | backend/services/llm_service.py: Gemini first, then Groq, then OpenRouter (LLM_PROVIDER_ORDER). A failed provider is skipped for LLM_COOLDOWN_SECONDS (60), then tried again, so Gemini comes back by itself. Used for the rewrite and the answer. Calls Groq/OpenRouter with httpx (no new packages). Keys: GROQ_API_KEY, OPENROUTER_API_KEY. Offline test: python -m scripts.check_llm_fallback. Safeguards on POST /chat: question max 500 chars, history max 20 messages of 2,000 chars (422 above that), rate limit 20 requests/min per IP in memory (429, backend/utils/rate_limit.py), Hebrew "service busy" message with 503 when all LLMs fail. Offline test: python -m scripts.check_safeguards |
| 17 | Tests and logging | TODO | Unit tests per layer, structured logging. |
| 18 | Refresh job + README | TODO | Scheduled refresh with log of added/updated/removed pages. |

## Last
Frontend (Hebrew right-to-left chat with history) and hosting.

## Working rules (from CLAUDE.md)
Explain the plan and list files first. No changes without approval. One task at a time. English only, simple words. After each task: summarize and explain how to test.
