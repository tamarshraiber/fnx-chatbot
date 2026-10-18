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

## Part D - Quality
| # | Step | Status | Notes |
|---|---|---|---|
| 14 | Eval set (~30 questions) | TODO | About 20 answerable + 10 unanswerable. |
| 15 | Tune retrieval | TODO | Recalibrate cutoff, hybrid search, Cohere Rerank. Keep only what helps. |
| 16 | Safeguards + backup LLM | TODO | Groq or OpenRouter as backup. |
| 17 | Tests and logging | TODO | Unit tests per layer, structured logging. |
| 18 | Refresh job + README | TODO | Scheduled refresh with log of added/updated/removed pages. |

## Last
Frontend (Hebrew right-to-left chat with history) and hosting.

## Working rules (from CLAUDE.md)
Explain the plan and list files first. No changes without approval. One task at a time. English only, simple words. After each task: summarize and explain how to test.
