"""
Pydantic models.

LLMOutput  - what the model must return (sent to Ollama as a JSON schema).
             It cites passages by NUMBER, so it can't invent doc/chunk ids.
ReviewResponse - what the agent returns to the website, with real citations
             looked up from those numbers.
"""
from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field, field_validator


class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class IssueCategory(str, Enum):
    SECURITY = "security"
    PERFORMANCE = "performance"
    MAINTAINABILITY = "maintainability"
    CORRECTNESS = "correctness"
    STYLE = "style"
    DOCUMENTATION = "documentation"


# ── What the LLM produces ───────────────────────────────────────────────────

class LLMIssue(BaseModel):
    category: IssueCategory
    severity: Severity
    line: int | None = None
    description: str
    suggestion: str
    sources: list[int] = Field(default_factory=list)


class LLMOutput(BaseModel):
    answer: str
    issues: list[LLMIssue] = Field(default_factory=list)
    sources: list[int] = Field(default_factory=list)
    confidence: float = 0.5
    abstained: bool = False
    abstain_reason: str | None = None

    @field_validator("confidence")
    @classmethod
    def _clamp(cls, v: float) -> float:
        return min(1.0, max(0.0, v))


# ── What the agent returns ──────────────────────────────────────────────────

class Source(BaseModel):
    n: int                      # the [n] number the answer refers to
    doc_id: str
    title: str
    chunk_id: str
    quote: str
    relevance: float            # 0-1 (sigmoid of the reranker score)


class Issue(BaseModel):
    category: IssueCategory
    severity: Severity
    line: int | None = None
    description: str
    suggestion: str
    sources: list[int] = Field(default_factory=list)


class ReviewResponse(BaseModel):
    answer: str
    issues: list[Issue] = Field(default_factory=list)
    sources: list[Source] = Field(default_factory=list)
    static_findings: list[dict] = Field(default_factory=list)
    confidence: float = 0.0
    abstained: bool = False
    abstain_reason: str | None = None
    warnings: list[str] = Field(default_factory=list)     # things the user should act on
    notes: list[str] = Field(default_factory=list)        # informational, e.g. guardrail activity
    language: str = ""          # language the request was reviewed as ("python" / "csharp")
    model: str = ""
    latency_s: float = 0.0
    tokens_in: int = 0
    tokens_out: int = 0
