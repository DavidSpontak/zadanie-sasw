"""
Supported languages, auto-detection, and the static analyzer for each.

To add a language: create knowledge_base/<key>/ with documents, add the key here,
and (optionally) an analyzer in src/tools/.
"""
from __future__ import annotations

import ast
import re

from src.tools import csharp_analyzer, python_analyzer

LANGUAGES = {"python": "Python", "csharp": "C#"}   # key (= knowledge_base subfolder) -> display name
DEFAULT_LANGUAGE = "python"

_ANALYZERS = {"python": python_analyzer.analyze, "csharp": csharp_analyzer.analyze}

_CSHARP_CODE_HINTS = [re.compile(p, re.MULTILINE) for p in [
    r";\s*$",                                                     # statement terminators
    r"^\s*[{}]\s*$",                                              # brace-only lines
    r"\b(public|private|protected|internal)\s+(static\s+)?(async\s+)?[\w<>\[\],?]+\s+\w+\s*\(",  # methods
    r"^\s*using\s+[\w.]+\s*;|\bnamespace\s+[\w.]+|\bclass\s+\w+\s*(:\s*\w+)?\s*\{?\s*$",
    r"\bvar\s+\w+\s*=",
    r"\b(string|int|bool|void|Task|decimal)\s+\w+\s*[=;(]",
]]
_CSHARP_QUESTION_RE = re.compile(
    r"(?<!\w)(c#|csharp|c-sharp|\.net|dotnet|asp\.net|blazor|linq|ef core|entity framework|nuget|"
    r"xunit|nunit|moq|nsubstitute|ilogger|async void|task\.whenall|httpclient)(?!\w)", re.IGNORECASE)
_PYTHON_QUESTION_RE = re.compile(r"(?<!\w)(python|pip|pytest|django|flask|fastapi|asyncio|pydantic)(?!\w)",
                                 re.IGNORECASE)


def detect_language(question: str, code: str | None) -> str:
    if code:
        hints = sum(bool(p.search(code)) for p in _CSHARP_CODE_HINTS)
        if hints >= 2:
            return "csharp"
        try:
            ast.parse(code)
            return "python"
        except SyntaxError:
            return "csharp" if hints else "python"
    if _CSHARP_QUESTION_RE.search(question) and not _PYTHON_QUESTION_RE.search(question):
        return "csharp"
    return DEFAULT_LANGUAGE


def analyze(code: str, language: str) -> dict:
    analyzer = _ANALYZERS.get(language)
    return analyzer(code) if analyzer else {"findings": [], "metrics": {}}
