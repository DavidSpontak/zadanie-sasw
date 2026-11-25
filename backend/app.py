"""
Backend API for the code review assistant.

Local dev (from the backend/ folder):
    uvicorn app:app --reload        ->  http://127.0.0.1:8000  (also serves ../frontend/index.html)

In Docker the frontend runs in its own nginx container and forwards /api to this service.
"""
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from src import config
from src.agent import CodeReviewAgent
from src.language import LANGUAGES
from src.llm_client import LLMError
from src.schema import ReviewResponse

agent: "CodeReviewAgent | None" = None


@asynccontextmanager
async def lifespan(_: FastAPI):
    global agent
    print(f"Loading knowledge base from {config.KB_DIR} ...", flush=True)
    agent = CodeReviewAgent.from_knowledge_base()   # loads KB + retrieval models once
    print(f"Indexed {len(agent.retriever.chunks)} chunks for: {', '.join(agent.retriever.languages)}.", flush=True)
    if agent.llm.is_ready():
        print(f"Ollama is ready with {config.LLM_MODEL}.", flush=True)
    else:
        print(f"WARNING: Ollama not reachable at {config.OLLAMA_URL} or '{config.LLM_MODEL}' not pulled.\n"
              f"         Start it with `ollama serve` and run `ollama pull {config.LLM_MODEL}`.", flush=True)
    yield
    agent.llm.close()


app = FastAPI(title="Code Review RAG", lifespan=lifespan)


class ReviewRequest(BaseModel):
    question: str = Field("", max_length=config.MAX_QUESTION_CHARS)
    code: str | None = Field(None, max_length=config.MAX_CODE_CHARS)
    language: Literal["auto", "python", "csharp"] = "auto"


@app.get("/api/health")
def health():
    return {
        "model": config.LLM_MODEL,
        "ollama_ready": agent.llm.is_ready(),
        "chunks": len(agent.retriever.chunks),
        "languages": {key: LANGUAGES.get(key, key) for key in agent.retriever.languages},
    }


@app.post("/api/review", response_model=ReviewResponse)
def review(req: ReviewRequest):  # plain `def`: FastAPI runs it in a thread, so the blocking LLM call is fine
    try:
        return agent.review(req.question, req.code, req.language)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except LLMError as e:
        raise HTTPException(503, str(e))


# Local dev convenience: serve the page from ../frontend if it exists (not present in the Docker image)
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
if (FRONTEND_DIR / "index.html").exists():
    @app.get("/", include_in_schema=False)
    def index():
        return FileResponse(FRONTEND_DIR / "index.html")

    app.mount("/fonts", StaticFiles(directory=FRONTEND_DIR / "fonts"), name="fonts")
