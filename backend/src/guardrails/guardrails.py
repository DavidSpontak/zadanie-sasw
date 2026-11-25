"""
Lightweight guardrails. The LLM has no tools, so the worst a prompt injection
can do is change the text it writes. These checks cover what still matters:

  1. Block obvious injection / jailbreak attempts in the user's question.
  2. Drop retrieved chunks that contain injections; redact secrets in the rest
     (so a security doc with an example key is still usable).
  3. Redact anything secret-looking from the final output.
"""
from __future__ import annotations

import re

INJECTION_PATTERNS = [re.compile(p, re.IGNORECASE) for p in [
    r"\b(ignore|disregard)\s+(all\s+)?(the\s+)?(previous|prior|above|your)\s+(instructions?|rules|prompt)",
    r"\bforget\s+(everything|all)\b",
    r"\b(reveal|print|output|show)\s+(me\s+)?(your\s+)?(full\s+)?system\s+prompt",
    r"\byou\s+are\s+now\s+(dan|an?\s+(unrestricted|different|new))\b",
    r"\bdo\s+anything\s+now\b",
    r"\bDAN\s+mode\b",
    r"\bjailbreak",
    r"\bpretend\s+(you\s+are|to\s+be)\s+(an?\s+)?(unrestricted|evil|unethical|unfiltered)",
    r"\bact\s+as\s+if\s+(you\s+have\s+)?no\s+(restrictions|rules|guidelines)",
    r"\b(disable|bypass)\s+(all\s+)?(safety|content|filters?|guidelines)",
    r"\bsystem\s+override\b",
]]

SECRET_PATTERNS = [re.compile(p, re.IGNORECASE) for p in [
    r"FAKE-SECRET-KEY[\w-]*",                         # planted test secrets in the KB
    r"SECRET_INTERNAL_DOCUMENT\w*",
    r"confidential\s+internal\s+api\s+key",
    r"\bsk-[A-Za-z0-9_-]{20,}",                       # OpenAI-style keys
    r"\bgh[pousr]_[A-Za-z0-9]{30,}",                  # GitHub tokens
    r"\bAKIA[0-9A-Z]{16}\b",                          # AWS access keys
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
    r"\b(?=[A-Za-z0-9]*\d)(?=[A-Za-z0-9]*[A-Za-z])[A-Za-z0-9]{32,}\b",  # long random tokens
]]


def find_injection(text: str) -> str | None:
    """Return the matched phrase if `text` looks like a prompt injection."""
    for pattern in INJECTION_PATTERNS:
        m = pattern.search(text)
        if m:
            return m.group(0)
    return None


def contains_secret(text: str) -> bool:
    return any(p.search(text) for p in SECRET_PATTERNS)


def redact_secrets(text: str) -> str:
    for p in SECRET_PATTERNS:
        text = p.sub("[REDACTED]", text)
    return text
