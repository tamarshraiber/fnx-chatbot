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

## Deployment
- Backend: Render, free web service, built from the `Dockerfile` (health check path `/health`).
- Frontend: Vercel, root folder `frontend`.
- Light mode: a free server has 512 MB of memory, and the full embedding model needs over 1 GB. The Dockerfile builds
  a compact copy of the same model (`scripts/build_onnx_model.py`) and sets `EMBEDDING_ONNX_DIR`. Questions are then
  embedded by the compact copy (about 300 MB for the whole server). The vectors in the database stay valid.
  Documents are always embedded by the full model, so crawling and uploading are not affected.

## Run locally
```
pip install -r requirements.txt
uvicorn backend.main:app --reload --port 8000
cd frontend && npm install && npm run dev
```
