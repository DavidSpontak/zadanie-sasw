"""
All settings in one place. Override any of them with an environment variable,
e.g.  LLM_MODEL=qwen2.5:3b uvicorn app:app
"""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KB_DIR = Path(os.getenv("KB_DIR", ROOT / "knowledge_base"))
CACHE_DIR = Path(os.getenv("CACHE_DIR", ROOT / ".cache"))

# ── LLM (Ollama) ─────────────────────────────────────────────────────────────
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
LLM_MODEL = os.getenv("LLM_MODEL", "qwen2.5:7b")
LLM_TEMPERATURE = 0.1
LLM_NUM_CTX = 8192        # Ollama's default context is too small for 6 passages + code
LLM_MAX_OUTPUT_TOKENS = 2048
LLM_TIMEOUT_S = 300

# ── Retrieval ────────────────────────────────────────────────────────────────
EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
RERANK_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"
# Documents are split at '##' headings, so each chunk is one topic. Sections longer
# than CHUNK_SIZE words are split further. Kept small because the embedding model
# only reads ~256 tokens and the reranker ~512; longer chunks get silently cut off.
CHUNK_SIZE = 250          # max words per chunk
CHUNK_OVERLAP = 40        # words carried over when a long section is split
CANDIDATES = 20           # BM25 / dense candidates before reranking
TOP_K = 5                 # passages per query after reranking
MAX_PASSAGES = 6          # passages sent to the LLM (across all queries)
DEDUP_THRESHOLD = 0.90    # cosine similarity above which two chunks count as duplicates
PASSAGE_CHARS = 1600      # each passage is cut to this length in the prompt

# Cross-encoder scores are logits: clearly relevant passages usually score > 0,
# unrelated ones around -10. If the best passage scores below this and the user
# sent no code, we abstain without calling the LLM. Tune it on your KB.
MIN_RERANK_SCORE = -4.0

# ── Input limits (protect the website / context window) ─────────────────────
MAX_QUESTION_CHARS = 2000
MAX_CODE_CHARS = 6000
