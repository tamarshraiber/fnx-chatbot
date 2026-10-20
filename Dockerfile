# Backend image for Render (free web service, 512 MB of memory).
# Stage 1 (builder) has torch and builds a compact copy of the embedding model. It is not part of the final image.
# Stage 2 (final) has no torch: only the compact model files and the code, so it needs about 300 MB at run time.

# ---------- Stage 1: build the compact model ----------
FROM python:3.11-slim AS builder
WORKDIR /build

# CPU-only torch (much smaller than the default build). Versions are the ones we tested.
RUN pip install --no-cache-dir torch==2.14.1 --index-url https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir \
    sentence-transformers==6.1.0 \
    onnx==1.23.2 \
    onnxruntime==1.31.0 \
    sentencepiece==0.2.2 \
    numpy==2.4.6 \
    python-dotenv==1.2.4

COPY backend ./backend
COPY scripts/build_onnx_model.py ./scripts/build_onnx_model.py
# Downloads the model, splits it, shrinks it, and fails the build if the result is too different from the full model.
RUN python -m scripts.build_onnx_model /onnx && rm -rf /onnx/.cache

# ---------- Stage 2: the server ----------
FROM python:3.11-slim

# Run as a normal user, not as root.
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    EMBEDDING_ONNX_DIR=/home/user/onnx
WORKDIR /home/user/app

# Only what the running chatbot needs (no torch, no crawler).
RUN pip install --no-cache-dir \
    python-dotenv==1.2.4 \
    google-genai==2.31.0 \
    supabase==2.33.0 \
    fastapi==0.143.2 \
    uvicorn==0.54.0 \
    cohere==7.2.0 \
    onnxruntime==1.31.0 \
    sentencepiece==0.2.2 \
    numpy==2.4.6

COPY --from=builder --chown=user /onnx /home/user/onnx
# The code. Secrets are NOT in the image: they come from the host's environment variables.
COPY --chown=user backend ./backend

# Render gives the port in $PORT (10000 if it is not set).
CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-10000}"]
