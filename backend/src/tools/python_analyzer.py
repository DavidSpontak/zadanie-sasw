"""
AST-based static checks for Python code. Deterministic, so the LLM gets
reliable facts (with correct line numbers) to build its review on.

Each finding has a `topic`, used as an extra knowledge-base search query.
"""
from __future__ import annotations

import ast
import re

# exact call name -> severity
DANGEROUS_CALLS = {
    "eval": "high",
    "exec": "high",
    "pickle.loads": "high",
    "pickle.load": "high",
    "marshal.loads": "high",
    "os.system": "high",
    "os.popen": "high",
    "yaml.load": "medium",
    "compile": "medium",
    "__import__": "medium",
}
SUBPROCESS_CALLS = {"subprocess.call", "subprocess.run", "subprocess.Popen", "subprocess.check_output"}
BLOCKING_IN_ASYNC = ("requests.", "time.sleep", "urllib.request.urlopen")
SQL_RE = re.compile(r"\b(SELECT|INSERT|UPDATE|DELETE)\b", re.IGNORECASE)
SECRET_RES = [
    (re.compile(r'(?i)\b(password|passwd|pwd)\s*=\s*["\'][^"\'\s]{4,}["\']'), "hardcoded_password"),
    (re.compile(r'(?i)\b(api_key|apikey|secret|secret_key|token)\s*=\s*["\'][^"\'\s]{8,}["\']'), "hardcoded_secret"),
]
SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}


def _finding(kind: str, line: int, severity: str, message: str, topic: str) -> dict:
    return {"type": kind, "line": line, "severity": severity, "message": message, "topic": topic}


def _call_name(node: ast.Call) -> str:
    try:
        return ast.unparse(node.func)
    except Exception:
        return ""


def _is_sql_string_building(node: ast.AST) -> bool:
    """'SELECT ... ' + x,  f'SELECT {x}',  'SELECT %s' % x,  'SELECT {}'.format(x)"""
    def has_sql_literal(n: ast.AST) -> bool:
        return any(isinstance(c, ast.Constant) and isinstance(c.value, str) and SQL_RE.search(c.value)
                   for c in ast.walk(n))

    if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Mod)):
        return has_sql_literal(node)
    if isinstance(node, ast.JoinedStr):
        return has_sql_literal(node) and any(isinstance(v, ast.FormattedValue) for v in node.values)
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "format":
        return has_sql_literal(node.func.value)
    return False


def analyze(code: str) -> dict:
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return {
            "findings": [_finding("syntax_error", e.lineno or 1, "high", f"Syntax error: {e.msg}", "python syntax error")],
            "metrics": {},
        }

    findings: list[dict] = []
    sql_lines: set[int] = set()

    for node in ast.walk(tree):
        # Functions: annotations, size, mutable defaults, blocking calls in async
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.returns is None and node.name != "__init__":
                findings.append(_finding("missing_return_annotation", node.lineno, "low",
                                         f"Function '{node.name}' has no return type annotation.", "type hints"))
            if len(node.args.args) > 5:
                findings.append(_finding("too_many_parameters", node.lineno, "medium",
                                         f"Function '{node.name}' has {len(node.args.args)} parameters.",
                                         "function with too many parameters"))
            length = (node.end_lineno or node.lineno) - node.lineno
            if length > 50:
                findings.append(_finding("long_function", node.lineno, "medium",
                                         f"Function '{node.name}' is {length} lines long.",
                                         "single responsibility principle long functions"))
            for default in node.args.defaults + [d for d in node.args.kw_defaults if d is not None]:
                if isinstance(default, (ast.List, ast.Dict, ast.Set)):
                    findings.append(_finding("mutable_default_argument", node.lineno, "medium",
                                             f"Function '{node.name}' uses a mutable default argument; use None instead.",
                                             "mutable default argument"))
            if isinstance(node, ast.AsyncFunctionDef):
                for sub in ast.walk(node):
                    if isinstance(sub, ast.Call) and _call_name(sub).startswith(BLOCKING_IN_ASYNC):
                        findings.append(_finding("blocking_call_in_async", sub.lineno, "high",
                                                 f"Blocking call {_call_name(sub)}() inside async function '{node.name}'.",
                                                 "blocking calls in async code asyncio"))

        # Calls: dangerous builtins, shell=True
        elif isinstance(node, ast.Call):
            name = _call_name(node)
            if name in DANGEROUS_CALLS:
                findings.append(_finding("dangerous_call", node.lineno, DANGEROUS_CALLS[name],
                                         f"Potentially dangerous call: {name}()", f"{name} security risk"))
            elif name in SUBPROCESS_CALLS and any(
                kw.arg == "shell" and isinstance(kw.value, ast.Constant) and kw.value.value is True
                for kw in node.keywords
            ):
                findings.append(_finding("dangerous_call", node.lineno, "high",
                                         f"{name}(shell=True) can allow command injection.", "command injection"))

        # Bare except
        elif isinstance(node, ast.ExceptHandler) and node.type is None:
            findings.append(_finding("bare_except", node.lineno, "medium",
                                     "Bare 'except:' also catches KeyboardInterrupt and SystemExit.",
                                     "bare except catch specific exceptions"))

        # SQL built from strings
        if _is_sql_string_building(node) and node.lineno not in sql_lines:
            sql_lines.add(node.lineno)
            findings.append(_finding("sql_string_building", node.lineno, "critical",
                                     "SQL query built by string formatting/concatenation (SQL injection risk).",
                                     "SQL injection parameterized queries"))

    for pattern, kind in SECRET_RES:
        for m in pattern.finditer(code):
            line = code[:m.start()].count("\n") + 1
            findings.append(_finding(kind, line, "critical", "Possible hardcoded secret.",
                                     "hardcoded secrets environment variables"))

    findings.sort(key=lambda f: (SEVERITY_ORDER[f["severity"]], f["line"]))

    branches = sum(isinstance(n, (ast.If, ast.For, ast.While, ast.ExceptHandler, ast.With,
                                  ast.Assert, ast.comprehension)) for n in ast.walk(tree))
    lines = code.splitlines()
    metrics = {
        "estimated_cyclomatic_complexity": 1 + branches,
        "total_lines": len(lines),
        "comment_lines": sum(1 for l in lines if l.strip().startswith("#")),
    }
    return {"findings": findings, "metrics": metrics}
