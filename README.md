---
title: Phoenix RAG Chatbot
emoji: 💬
colorFrom: orange
colorTo: red
sdk: docker
app_port: 7860
pinned: false
---

# Phoenix RAG chatbot

A Hebrew question-answering chatbot for the fnx.co.il website. It answers only from the website's own pages and
says so when the answer is not there.

## How it works
1. The question is turned into numbers with a local model (`intfloat/multilingual-e5-base`).
2. The closest text chunks are found in Supabase (pgvector).
3. Gemini writes the answer from those chunks only. If Gemini fails, OpenRouter is used as a backup.
4. The answer is streamed to the React page.

## Parts
- `backend/` - FastAPI server (`/chat`, `/chat/stream`, `/health`) and the ingestion code.
- `frontend/` - React + Vite chat page.
- `supabase/` - database setup.

## Settings (environment variables)
Secrets, set in the hosting dashboard and never committed: `GEMINI_API_KEY`, `SUPABASE_URL`, `SUPABASE_KEY`,
`OPENROUTER_API_KEY`.
Plain settings: `CORS_ORIGINS` (the web addresses allowed to call the API, separated by commas) on the backend, and
`VITE_API_URL` (the backend address) on the frontend.

## Run locally
```
pip install -r requirements.txt
uvicorn backend.main:app --reload --port 8000
cd frontend && npm install && npm run dev
```
