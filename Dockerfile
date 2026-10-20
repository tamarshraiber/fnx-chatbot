# Backend image for Hugging Face Spaces (Docker type). The Space listens on port 7860.
FROM python:3.11-slim

# Hugging Face runs the container as user 1000, so we create the same user.
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    HF_HOME=/home/user/.cache/huggingface \
    PYTHONUNBUFFERED=1
WORKDIR /home/user/app

# 1. CPU-only torch (much smaller than the default build, and the Space has no GPU).
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# 2. Only the packages the running chatbot needs. crawl4ai (the crawler) is left out on purpose.
RUN pip install --no-cache-dir \
    python-dotenv==1.2.4 \
    google-genai==2.31.0 \
    sentence-transformers==6.1.0 \
    supabase==2.33.0 \
    fastapi==0.143.2 \
    uvicorn==0.54.0 \
    cohere==7.2.0

# 3. Download the embedding model now, at build time, so the server does not download it at every start.
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('intfloat/multilingual-e5-base')"

# 4. The code. Secrets are NOT in the image: they come from the Space settings.
COPY --chown=user backend ./backend

EXPOSE 7860
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "7860"]
