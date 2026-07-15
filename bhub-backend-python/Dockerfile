# BHUB Backend - Dockerfile
# Python 3.12 with FastAPI

FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Set work directory
WORKDIR /app

# Install system dependencies
# - build-essential/cmake/git: needed to build native wheels (e.g. optional llama-cpp-python)
# - libgomp1: OpenMP runtime required by torch / scikit-learn
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    git \
    curl \
    libffi-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
# Install the CPU-only build of torch first to avoid pulling the large CUDA wheels
# (this container runs inference on CPU). This satisfies the torch>=2.5 pin below.
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu
# Install everything except the optional local-LLM dependency (llama-cpp-python),
# which is disabled by default and only needed for offline GGUF inference.
RUN grep -v '^llama-cpp-python' requirements.txt > /tmp/requirements.core.txt && \
    pip install --no-cache-dir -r /tmp/requirements.core.txt
# Best-effort install of the optional local LLM backend; the app degrades
# gracefully (try/except ImportError) when it is absent.
RUN pip install --no-cache-dir 'llama-cpp-python>=0.2.0' \
    || echo "WARN: llama-cpp-python not installed (optional local LLM disabled)"

# Pre-download the sentence-transformers embedding model into the image so the
# container starts fast and works without a runtime network dependency.
ENV HF_HOME=/app/.cache/huggingface \
    SENTENCE_TRANSFORMERS_HOME=/app/.cache/huggingface \
    EMBEDDING_MODEL=paraphrase-multilingual-MiniLM-L12-v2
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('${EMBEDDING_MODEL}')"

# Copy application code
COPY . .

# Create directories
RUN mkdir -p /app/uploads/pdfs /app/logs

# Create non-root user
RUN adduser --disabled-password --gecos '' appuser && \
    chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
