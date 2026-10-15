# DECISIONS.md - Phoenix (fnx.co.il) Hebrew RAG Chatbot

Paste this file at the start of a new chat. Continue from "Next steps".

## Goal
Hebrew chatbot that answers ONLY from public fnx.co.il content, always cites the source URL, and says "This is not mentioned on the website" (+ refers to customer service) when info is missing. Top metric: no hallucinations. Deliverables: working chatbot with link, demo of 20-30 questions, source code, run instructions, short summary (collection, chunk selection, limitations, refresh process).

## Working rules (CLAUDE.md)
Explain plan first, list files, no changes without approval, one task at a time, simple English, summarize + how to test after each task. The user prefers running install commands themselves.

## Decisions and reasons
| Area | Decision | Why |
|---|---|---|
| Languages | Python (data pipeline and backend); frontend decided later | One language for crawl, RAG and API; best libraries |
| Crawler | Crawl4AI, run locally | Free, no page limit, handles JS, polite-rate control |
| Answer LLM | Gemini Flash (free tier) | Good Hebrew, free; user has Google account |
| Embeddings | Gemini Embedding | Same key, good Hebrew, free tier |
| Vector DB | Supabase pgvector | Free cloud DB; vector + keyword search together |
| Backend | Python (FastAPI), layered: controllers, services, repositories, models, ingestion. Hosting decided after it works locally | Clean separation; one language. Replaces the earlier Next.js on Vercel decision |
| UI | Hebrew right-to-left chat with history; framework and host decided later | Requirement |
| Retrieval | Vector first -> add keyword (hybrid) -> test Cohere Rerank | Keep only what tests show helps |
| Secrets | Keys only in `.env` / Vercel settings; delete after hackathon | Security |
| Rate limits | Exponential backoff on 429, short prompts | Free-tier limits |
| Backup LLM | Groq or OpenRouter, added after main flow works | User decision |

Rejected: Streamlit and local Chroma (weak fit for a public chat app with cloud DB), Next.js API on Vercel (replaced by Python backend), Firecrawl (1,000-page limit), Jina Reader (single pages), Ollama/Groq as main model (weaker Hebrew, limits).

## Architecture
Crawler (local Python) -> clean HTML -> chunks with title + URL + collection date -> Gemini embeddings -> Supabase.
Python backend: question -> retrieve chunks -> if relevance too low, fixed "not on the website" reply + customer service referral; otherwise Gemini answers in Hebrew from chunks only, with source URL (structured output). Edge cases: personal policy questions and professional advice get an explanation + referral.

Layers: controller (HTTP only) -> service (logic) -> repository (Supabase only); models hold schemas. Ingestion scripts run locally, not on the server.

```
backend/
  main.py, config.py
  controllers/chat_controller.py
  services/chat_service.py, retrieval_service.py, generation_service.py
  models/schemas.py, db_models.py
  repositories/vector_repository.py
  ingestion/config.py, scraper.py, chunker.py, embed_upload.py
  utils/retry.py
data/raw/, data/chunks/
supabase/schema.sql
frontend/   (later)
eval/       (questions.json, run_eval.py)
```

## Data freshness and speed
- Two separate paths:
  - Offline (slow, run by us): crawl -> chunk -> embed -> store in Supabase. Users never wait for it.
  - Online (fast, per question): embed question, vector search in Supabase, one Gemini Flash call. Target: answer in about 2-4 seconds. The website is NEVER contacted while answering.
- Fetch once, then reuse the stored copy (the database is the cache).
- Refresh: sitemap `lastmod` per URL plus a content hash. Re-crawl and re-embed only new or changed pages; delete chunks of removed pages. Manual run for the hackathon, maybe a weekly job later.
- Each chunk stores `url`, `lastmod`, `content_hash`, `crawled_at`.
- Limitation to state: between refreshes the bot may show old information.
- Speed extras if needed: stream the answer, short prompts, small top-k (4-6), cache repeated questions.

## Other decisions
- Chat history: memory inside the conversation only (frontend sends the last few messages with each question). Nothing saved on the server.
- Folder path: do not move it now. Finish planning first. If a move is needed later, do it then and start a new chat from this file (Claude Code chats are tied to the folder path).
- Frontend choice and hosting: decided later.

## Quality bar (goal: high-caliber, not just hackathon-level)
Embedding is done by a script (`embed_upload.py`), never by hand. "Manual" only meant that we start the run. Build a small working version first, then add these in priority order:
1. One-command pipeline: crawl, clean, chunk, embed, upload (`python -m backend.ingestion.run`).
2. Incremental and idempotent runs: only changed pages (by `lastmod` or hash); re-running never creates duplicates.
3. Automatic refresh: scheduled job (for example GitHub Actions, weekly), with a log of added, updated and removed pages. Hosting decided later.
4. Measured evaluation: about 30 questions scored automatically (accuracy, correct citations, false "not on the website" replies); keep score history so each tuning change is proven.
5. Resilience: retries with backoff, resume after a crash, failed pages reported.
6. Index versioning: load new data as a new version and switch only when complete.
7. Quality gates: sanity checks on page and chunk counts, and the eval set must pass before a refresh goes live.
8. Answer safeguards: verify each cited URL was actually retrieved; relevance threshold; conversation context; personal-policy and professional-advice handling.
9. Engineering basics: unit tests per layer, typed schemas, structured logging, secrets only in `.env`, README with architecture notes.

## Website findings (read-only check)
- robots.txt: one group for all crawlers, 16 blocked path patterns, no crawl-delay, sitemap at /sitemap.xml.
- Sitemap: one URL list (~630KB), every URL has lastmod (useful for refresh). Not fully read yet.
- Pages are readable text (not an empty JS shell). Claims hub is mostly navigation; real explanations are on `/claims-customer-service/claims-*` sub-pages and product "information" sections. No clear FAQ section.
- Claim forms/logins live on subdomains (my/forms/*claim.fnx.co.il).

## Proposed crawl scope (NOT YET APPROVED)
Include: claims sub-pages, product pages + info sections (car, apartment, mortgage, travel, health, life, pets), customer service, relevant guides. Exclude: login/form subdomains, robots.txt-blocked paths, calculators/quote pages, English pages. Rate: 1-2 seconds between requests.

## Status
- Windows 11, PowerShell. Project folder `c:\תמר\Hackathon` (Hebrew in path; if tools fail, move to e.g. `C:\dev\Hackathon`, with approval).
- Done by user: `.venv`, `crawl4ai`, Chromium (`crawl4ai-setup`), `python-dotenv`, `google-genai`. `crawl4ai-doctor` passed.
- Files in project: `CLAUDE.md`, `.gitignore`, this file. Already a Git repo (one initial commit).

## Testing plan
About 20 answerable + 10 unanswerable questions; measure accuracy and hallucinations; test follow-ups; optional NotebookLM comparison on ~50 pages.

## Next steps
1. User approves the crawl scope.
2. Approve step 3: create `backend/ingestion/config.py`, `backend/ingestion/scraper.py`, `.env.example`, `data/raw/`; test run on ~5 pages.
3. Then: chunking + embeddings, Supabase setup (user creates account/keys), backend layers (repository, services, controller), frontend, retrieval tuning, test set, backup LLM, README + summary.
4. After it works locally: choose hosting for backend and frontend, then deploy (Git/GitHub).
