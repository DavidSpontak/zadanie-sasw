"""
Minimal Ollama client.

Uses Ollama structured outputs (`format` = JSON schema, Ollama >= 0.5), so the
model can only produce JSON that matches the Pydantic model. We still validate
and retry once or twice in case of a bad generation.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Type, TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from src import config

T = TypeVar("T", bound=BaseModel)


class LLMError(RuntimeError):
    pass


@dataclass
class LLMStats:
    tokens_in: int = 0
    tokens_out: int = 0


class LLMClient:
    def __init__(self, model: str = config.LLM_MODEL, base_url: str = config.OLLAMA_URL):
        self.model = model
        self._http = httpx.Client(base_url=base_url, timeout=config.LLM_TIMEOUT_S)

    def chat_json(self, system: str, user: str, schema: Type[T], retries: int = 2) -> tuple[T, LLMStats]:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "stream": False,
            "format": schema.model_json_schema(),
            "options": {
                "temperature": config.LLM_TEMPERATURE,
                "num_ctx": config.LLM_NUM_CTX,
                "num_predict": config.LLM_MAX_OUTPUT_TOKENS,
                "seed": 42,
            },
        }
        stats = LLMStats()
        last_error: Exception | None = None

        for attempt in range(retries + 1):
            payload["options"]["seed"] = 42 + attempt
            try:
                r = self._http.post("/api/chat", json=payload)
                r.raise_for_status()
            except httpx.ConnectError as e:
                raise LLMError(f"Cannot reach Ollama at {config.OLLAMA_URL}. Is `ollama serve` running?") from e
            except httpx.HTTPStatusError as e:
                raise LLMError(f"Ollama error {e.response.status_code}: {e.response.text[:200]}") from e

            data = r.json()
            stats.tokens_in += data.get("prompt_eval_count", 0)
            stats.tokens_out += data.get("eval_count", 0)
            try:
                return schema.model_validate_json(data["message"]["content"]), stats
            except (ValidationError, KeyError) as e:
                last_error = e

        raise LLMError(f"Model output did not match {schema.__name__}: {last_error}")

    def is_ready(self) -> bool:
        """True if Ollama is up and the model has been pulled."""
        try:
            names = [m["name"] for m in self._http.get("/api/tags", timeout=3).json().get("models", [])]
        except Exception:
            return False
        return any(n == self.model or n == f"{self.model}:latest" for n in names)

    def close(self):
        self._http.close()
