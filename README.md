# Code Review RAG Assistant

A retrieval-augmented code review assistant for **Python and C#**. Ask a best-practice question
or paste code, and it answers from the documents in `backend/knowledge_base/`, citing the passages it used.
It runs fully locally with one LLM (`qwen2.5:7b` via Ollama).

```
┌──────────────┐   /api/*   ┌──────────────────────┐   HTTP   ┌──────────────────┐
│  frontend    │ ─────────► │  backend (FastAPI)   │ ───────► │  Ollama          │
│  nginx :8080 │            │  retrieval + agent   │          │  qwen2.5:7b      │
└──────────────┘            └──────────────────────┘          └──────────────────┘
   index.html                 knowledge_base/                   on your machine, or
                              python/  csharp/                  optional 3rd container
```

## Run with Docker (recommended)

Requirements: Docker Desktop (or Docker Engine + Compose) and [Ollama](https://ollama.com) installed on your machine.

```bash
ollama pull qwen2.5:7b
docker compose up --build
```

Open http://localhost:8080. API docs: http://localhost:8080/docs.

The first build takes a few minutes: it installs PyTorch (CPU build) and downloads the embedding
and reranker models into the image. Later starts take a few seconds.

The backend container talks to the Ollama running on your machine through `host.docker.internal`,
so the model keeps using your GPU.

### Option: Ollama in Docker too

```bash
docker compose -f docker-compose.yml -f docker-compose.ollama.yml up --build
```

This adds an `ollama` container and downloads `qwen2.5:7b` (~4.7 GB) on the first start; the
backend waits until the download has finished. Without GPU passthrough the model runs on CPU,
which is much slower. For an NVIDIA GPU, uncomment the `deploy:` block in `docker-compose.ollama.yml`
(needs the NVIDIA Container Toolkit on Linux, or Docker Desktop with WSL2 on Windows).
On macOS Docker can't use the GPU, so keep Ollama native there.

## Run without Docker (development)

Requirements: Python 3.10+ and Ollama.

```bash
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
ollama pull qwen2.5:7b
uvicorn app:app --reload
```

Open http://127.0.0.1:8000. In this mode the backend also serves `frontend/index.html`.

Quick test without the website:

```bash
python -m src.agent "What is SQL injection and how can it be prevented in Python?"
python -m src.agent "Why should I avoid async void in C#?"
```

## Languages

The language picker on the page has **Auto-detect**, **Python** and **C#**.
Auto-detect looks at the pasted code (or a ```` ```csharp ```` fence), then at keywords in the question
(C#, .NET, LINQ, EF Core, xUnit, ...); otherwise it uses Python.

Each language has its own folder in `backend/knowledge_base/`, and retrieval only searches the folder
for the chosen language. Documents placed directly in `knowledge_base/` (not in a subfolder) are used for all languages.

| | Python | C# |
|---|---|---|
| Knowledge base | `knowledge_base/python/` (12 docs) | `knowledge_base/csharp/` (10 docs) |
| Static analysis | AST-based (`src/tools/python_analyzer.py`) | pattern-based heuristics (`src/tools/csharp_analyzer.py`) |

Some Python documents are test fixtures on purpose: `security_guide_distractor.md` contains wrong
advice, `performance_guide_duplicate.md` is a near-duplicate, and `dependency_management.md` contains
a prompt injection and a fake secret. The guardrails and deduplication handle them.

**Adding a language:** create `knowledge_base/<key>/` with Markdown documents (one topic per `##` section),
add the key to `LANGUAGES` in `src/language.py` and to the `language` options in `app.py` and `frontend/index.html`.
A static analyzer is optional.

## How it works

```
question (+ code) + language
  -> input guardrail           blocks prompt-injection / jailbreak questions
  -> static analysis           Python: AST checks, C#: pattern checks (SQL built from strings, async void, ...)
  -> hybrid retrieval          in that language's documents:
                               BM25 + MiniLM embeddings -> RRF fusion -> dedup -> cross-encoder rerank
  -> document guardrail        drops passages containing injections, redacts secrets
  -> early abstain             no code and no relevant passage -> "not covered", no LLM call
  -> one LLM call              JSON output enforced by schema; cites passages by number
  -> output guardrail          numbers mapped to real citations, secrets redacted
```

Documents are split into one chunk per `##` section, so each chunk is a single topic and fits fully
into the embedding and reranker models.

## Configuration

All settings are in `backend/src/config.py` and can be overridden with environment variables
(`LLM_MODEL`, `OLLAMA_URL`, `KB_DIR`, `CACHE_DIR`). With Docker, set them in a `.env` file next to
`docker-compose.yml`, e.g. `LLM_MODEL=qwen2.5:3b`.

`MIN_RERANK_SCORE` decides when the assistant refuses because the knowledge base doesn't cover a
question. To pick a good value, run:

```bash
cd backend && python check_retrieval.py          # local
docker compose exec backend python check_retrieval.py   # Docker
```

It prints the best retrieval score for questions that should and shouldn't be answered (in both
languages) and suggests a cutoff.

The knowledge base folder is mounted into the backend container, so you can edit documents without
rebuilding: `docker compose restart backend` re-indexes them.

## API

- `POST /api/review` with `{"question": "...", "code": "...", "language": "auto" | "python" | "csharp"}`
  (code optional) returns the answer (with [n] citation markers), issues, cited sources, static-analysis findings,
  warnings, notes (guardrail activity), language, confidence and latency.
- `GET /api/health` shows whether Ollama and the model are ready, and which languages are indexed.

## Troubleshooting

- **"Ollama not reachable" in the backend logs** (`docker compose logs backend`): make sure Ollama is
  running and the model is pulled (`ollama list`). On Linux, Ollama only listens on 127.0.0.1 by default;
  start it with `OLLAMA_HOST=0.0.0.0 ollama serve` so containers can reach it.
- **"The model took too long"**: on CPU a 7B model can need minutes per answer. Use a GPU, a smaller
  model (`LLM_MODEL=qwen2.5:3b`), or shorter code.
- **Port 8080 in use**: change `"8080:80"` in `docker-compose.yml`.

## Project structure

```
docker-compose.yml            frontend + backend (uses Ollama on your machine)
docker-compose.ollama.yml     optional: adds an Ollama container
frontend/
  index.html                  the web page
  fonts/                      Atkinson Hyperlegible Next + Mono (SIL Open Font License), served locally
  nginx.conf                  serves the page, forwards /api to the backend
  Dockerfile
backend/
  app.py                      FastAPI API
  check_retrieval.py          helper to tune MIN_RERANK_SCORE
  knowledge_base/python/      Python documents
  knowledge_base/csharp/      C# documents
  src/
    config.py                 all settings
    agent.py                  the pipeline
    language.py               languages, auto-detection, analyzer per language
    llm_client.py             Ollama client with schema-enforced JSON
    schema.py                 Pydantic models
    retrieval/hybrid_retriever.py
    tools/python_analyzer.py
    tools/csharp_analyzer.py
    guardrails/guardrails.py
  Dockerfile
```
