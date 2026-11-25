"""
Pattern-based static checks for C# code (there is no C# parser in Python, so
these are heuristics). Each rule reports the line it matched, so the LLM gets
reliable line numbers.

Each finding has a `topic`, used as an extra knowledge-base search query.
"""
from __future__ import annotations

import re

SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
SQL = r"\b(SELECT|INSERT|UPDATE|DELETE)\b"
# EF Core methods that turn an interpolated string into SQL parameters (safe)
EF_SAFE = re.compile(r"\b(FromSql|FromSqlInterpolated|ExecuteSql|ExecuteSqlInterpolated|ExecuteSqlAsync|"
                     r"ExecuteSqlInterpolatedAsync|SqlQuery)\b\s*(<[^>]*>)?\s*\(\s*\$")

# (type, severity, pattern, message, topic)
RULES = [
    ("sql_string_building", "critical",
     re.compile(rf'"[^"\n]*{SQL}[^"\n]*"\s*\+|\$@?"[^"\n]*{SQL}[^"\n]*\{{|@\$"[^"\n]*{SQL}[^"\n]*\{{|'
                rf'string\.Format\(\s*"[^"\n]*{SQL}', re.IGNORECASE),
     "SQL query built by concatenation/interpolation (SQL injection risk). Use parameters.",
     "SQL injection parameterized queries SqlCommand"),
    ("async_void", "high", re.compile(r"\basync\s+void\s+\w+\s*\("),
     "'async void' can't be awaited and crashes the process on unhandled exceptions; return Task.",
     "async void methods"),
    ("sync_over_async", "high", re.compile(r"\.(Result|Wait\(\)|GetAwaiter\(\)\s*\.GetResult\(\))(?![\w(])"),
     "Blocking on a Task (.Result / .Wait() / GetResult()) can deadlock or starve the thread pool; use await.",
     "blocking on async code .Result .Wait deadlock"),
    ("empty_catch", "high", re.compile(r"\bcatch\s*(\([^)]*\))?\s*\{\s*\}"),
     "Empty catch block silently swallows exceptions.",
     "exception handling catch specific exceptions"),
    ("insecure_deserialization", "critical",
     re.compile(r"\b(BinaryFormatter|SoapFormatter|NetDataContractSerializer|LosFormatter)\b"),
     "Insecure deserializer: can execute attacker-controlled code. Use System.Text.Json.",
     "insecure deserialization BinaryFormatter"),
    ("insecure_deserialization", "high",
     re.compile(r"TypeNameHandling\s*=\s*TypeNameHandling\.(All|Auto|Objects|Arrays)"),
     "Newtonsoft TypeNameHandling other than None allows type injection from untrusted JSON.",
     "insecure deserialization TypeNameHandling"),
    ("command_injection", "high",
     re.compile(r"Process\.Start\([^;]*?(\+|\$\")|\bArguments\s*=\s*(\$\"[^\"\n]*\{|[^;\n]*\+)"),
     "Process arguments built from strings (command injection risk). Use ProcessStartInfo.ArgumentList.",
     "command injection Process.Start ArgumentList"),
    ("path_traversal", "medium",
     re.compile(r"\b(File\.\w+|Directory\.\w+|new\s+FileStream)\(\s*(\"[^\"\n]*\"\s*\+|\$\"[^\"\n]*\{)"),
     "File path built from strings; validate it stays inside the allowed folder (path traversal).",
     "path traversal Path.GetFullPath"),
    ("hardcoded_secret", "critical",
     re.compile(r'(?i)\b\w*(password|passwd|pwd|secret|apikey|api_key|accesskey|token)\w*\s*=\s*"[^"\s]{6,}"'),
     "Possible hardcoded secret.", "hardcoded secrets user secrets configuration"),
    ("hardcoded_secret", "critical",
     re.compile(r'(?i)"[^"\n]*\b(password|pwd)\s*=\s*[^;"\s]{3,}'),
     "Connection string contains an inline password.", "hardcoded secrets connection strings"),
    ("weak_hash", "high",
     re.compile(r"\b(MD5|SHA1)\.(Create|HashData)\b|new\s+(MD5CryptoServiceProvider|SHA1Managed|SHA1CryptoServiceProvider)\b"),
     "MD5/SHA1 are broken for security use; for passwords use PBKDF2 (Rfc2898DeriveBytes.Pbkdf2).",
     "password hashing"),
    ("httpclient_per_call", "medium", re.compile(r"\bnew\s+HttpClient\s*\("),
     "Creating HttpClient per call can exhaust sockets; use IHttpClientFactory or one shared instance.",
     "HttpClient IHttpClientFactory socket exhaustion"),
    ("count_instead_of_any", "low", re.compile(r"\.Count\(\)\s*(>\s*0|!=\s*0|>=\s*1)\b"),
     "Use Any() instead of Count() > 0; Count() may enumerate the whole sequence.",
     "LINQ Any vs Count"),
]
CATCH_VAR_RE = re.compile(r"\bcatch\s*\(\s*[\w.]+\s+(\w+)\s*\)")
BRANCH_RE = re.compile(r"\b(if|for|foreach|while|case|catch)\b|&&|\|\||\?\?")


def _finding(kind: str, line: int, severity: str, message: str, topic: str) -> dict:
    return {"type": kind, "line": line, "severity": severity, "message": message, "topic": topic}


def analyze(code: str) -> dict:
    lines = code.splitlines()
    line_of = lambda pos: code.count("\n", 0, pos) + 1
    commented = lambda pos: "//" in code[code.rfind("\n", 0, pos) + 1:pos]   # match is after // on its line

    findings: list[dict] = []
    seen: set[tuple[str, int]] = set()

    def add(kind, pos, severity, message, topic):
        line = line_of(pos)
        if (kind, line) not in seen and not commented(pos):
            seen.add((kind, line))
            findings.append(_finding(kind, line, severity, message, topic))

    for kind, severity, pattern, message, topic in RULES:
        for m in pattern.finditer(code):
            if kind == "sql_string_building" and EF_SAFE.search(lines[line_of(m.start()) - 1]):
                continue  # EF Core FromSql($"...{x}") is parameterized
            add(kind, m.start(), severity, message, topic)

    # Thread.Sleep only matters in async code
    if re.search(r"\basync\b", code):
        for m in re.finditer(r"\bThread\.Sleep\(", code):
            add("blocking_sleep", m.start(), "medium",
                "Thread.Sleep blocks a thread; in async code use 'await Task.Delay'.", "Task.Delay vs Thread.Sleep async")

    # `throw ex;` inside a catch resets the stack trace
    for name in set(CATCH_VAR_RE.findall(code)):
        for m in re.finditer(rf"\bthrow\s+{re.escape(name)}\s*;", code):
            add("rethrow_loses_stack_trace", m.start(), "medium",
                f"'throw {name};' resets the stack trace; use 'throw;'.", "rethrow exception throw; stack trace")

    findings.sort(key=lambda f: (SEVERITY_ORDER[f["severity"]], f["line"]))
    metrics = {
        "estimated_cyclomatic_complexity": 1 + len(BRANCH_RE.findall(code)),
        "total_lines": len(lines),
        "comment_lines": sum(1 for l in lines if l.strip().startswith("//")),
    }
    return {"findings": findings, "metrics": metrics}
