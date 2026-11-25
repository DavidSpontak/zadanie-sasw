FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/app/.hf

WORKDIR /app

# CPU-only PyTorch: the embedding and reranker models are small, and this keeps the
# image ~2 GB smaller than the default CUDA build. The LLM runs in Ollama, not here.
RUN pip install torch --index-url https://download.pytorch.org/whl/cpu

COPY requirements.txt .
RUN pip install -r requirements.txt

# Download the embedding + reranker models at build time, so the container starts offline
COPY src/__init__.py src/config.py src/
RUN python -c "from sentence_transformers import SentenceTransformer, CrossEncoder; \
from src import config; SentenceTransformer(config.EMBED_MODEL); CrossEncoder(config.RERANK_MODEL)"
# Models are in the image now: don't contact Hugging Face at runtime
ENV HF_HUB_OFFLINE=1

COPY . .

# Pre-compute knowledge-base embeddings (rebuilt automatically at startup if the KB changes)
RUN python -c "from src.retrieval.hybrid_retriever import HybridRetriever; HybridRetriever.from_folder()"

EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=5s --start-period=60s --retries=10 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health', timeout=4)"

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
