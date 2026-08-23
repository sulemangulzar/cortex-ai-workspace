from __future__ import annotations

import ast
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

CODE_EXTENSIONS = {
    ".py",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".java",
    ".go",
    ".rs",
    ".rb",
    ".php",
    ".cs",
}

PYTHON_DB_CALLS = {
    "execute",
    "scalars",
    "scalar",
    "query",
    "select",
    "get",
    "filter",
    "filter_by",
}
NETWORK_CALL_NAMES = {"fetch", "request", "get", "post", "put", "patch", "delete"}


def _safe_relative_path(path: str) -> Path:
    candidate = Path(path.replace("\\", "/"))
    parts = [part for part in candidate.parts if part not in {"", ".", ".."}]
    return Path(*parts) if parts else Path("generated.py")


def _code_files_only(files: dict[str, str]) -> dict[str, str]:
    return {
        name: content
        for name, content in files.items()
        if Path(name).suffix.lower() in CODE_EXTENSIONS and isinstance(content, str)
    }


def run_bandit(files: dict[str, str]) -> dict[str, Any]:
    """Run Bandit against generated Python files without executing user code."""
    python_files = {
        name: content
        for name, content in files.items()
        if Path(name).suffix.lower() == ".py" and isinstance(content, str)
    }
    if not python_files:
        return {"scanner": "bandit", "skipped": True, "reason": "No Python files to scan", "results": []}

    with tempfile.TemporaryDirectory(prefix="cortex-bandit-") as tmp:
        root = Path(tmp)
        for name, content in python_files.items():
            target = root / _safe_relative_path(name)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")

        completed = subprocess.run(
            [sys.executable, "-m", "bandit", "-r", str(root), "-f", "json"],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        stdout = completed.stdout.strip()
        stderr = completed.stderr.strip()
        try:
            parsed: dict[str, Any] = json.loads(stdout) if stdout else {}
        except json.JSONDecodeError:
            parsed = {"raw_stdout": stdout}

        # Remove temp-dir prefixes so persisted output references generated paths, not local temp paths.
        root_prefix = str(root) + "/"
        for result in parsed.get("results", []) if isinstance(parsed.get("results"), list) else []:
            filename = result.get("filename")
            if isinstance(filename, str):
                result["filename"] = filename.replace(root_prefix, "")

        parsed.update(
            {
                "scanner": "bandit",
                "returncode": completed.returncode,
                "stderr": stderr,
                "skipped": False,
            }
        )
        return parsed


class _PythonPerformanceVisitor(ast.NodeVisitor):
    def __init__(self, filename: str) -> None:
        self.filename = filename
        self.loop_depth = 0
        self.findings: list[dict[str, Any]] = []

    def visit_For(self, node: ast.For) -> Any:
        self._visit_loop(node)

    def visit_AsyncFor(self, node: ast.AsyncFor) -> Any:
        self._visit_loop(node)

    def visit_While(self, node: ast.While) -> Any:
        self._visit_loop(node)

    def visit_Call(self, node: ast.Call) -> Any:
        call_name = self._call_name(node.func)
        if self.loop_depth > 0 and call_name:
            lower_name = call_name.lower()
            if any(token in lower_name for token in PYTHON_DB_CALLS) or any(token in lower_name for token in NETWORK_CALL_NAMES):
                self.findings.append(
                    {
                        "type": "loop_io_or_db_call",
                        "severity": "med",
                        "file": self.filename,
                        "line": getattr(node, "lineno", None),
                        "message": f"Potential repeated DB/network call inside loop: {call_name}",
                    }
                )
            if lower_name.endswith(".all") or lower_name == "all":
                self.findings.append(
                    {
                        "type": "unbounded_collection_load",
                        "severity": "med",
                        "file": self.filename,
                        "line": getattr(node, "lineno", None),
                        "message": "Potential unbounded .all() call; confirm pagination/limits are used.",
                    }
                )
        self.generic_visit(node)

    def _visit_loop(self, node: ast.stmt) -> None:
        if self.loop_depth > 0:
            self.findings.append(
                {
                    "type": "nested_loop",
                    "severity": "low",
                    "file": self.filename,
                    "line": getattr(node, "lineno", None),
                    "message": "Nested loop detected; verify input sizes and complexity.",
                }
            )
        self.loop_depth += 1
        self.generic_visit(node)
        self.loop_depth -= 1

    def _call_name(self, node: ast.AST) -> str | None:
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            base = self._call_name(node.value)
            return f"{base}.{node.attr}" if base else node.attr
        return None


def run_performance_static_scan(files: dict[str, str]) -> dict[str, Any]:
    """Run lightweight static performance heuristics against generated code files."""
    findings: list[dict[str, Any]] = []
    scanned_files = 0

    for filename, content in _code_files_only(files).items():
        scanned_files += 1
        suffix = Path(filename).suffix.lower()
        lower_content = content.lower()

        if suffix == ".py":
            try:
                tree = ast.parse(content)
            except SyntaxError as exc:
                findings.append(
                    {
                        "type": "syntax_unscanned",
                        "severity": "low",
                        "file": filename,
                        "line": exc.lineno,
                        "message": "Python file could not be parsed for performance checks.",
                    }
                )
            else:
                visitor = _PythonPerformanceVisitor(filename)
                visitor.visit(tree)
                findings.extend(visitor.findings)

        if ".all()" in lower_content and not any(token in lower_content for token in ("limit(", "offset(", "paginate", "page_size")):
            findings.append(
                {
                    "type": "missing_pagination_hint",
                    "severity": "med",
                    "file": filename,
                    "line": None,
                    "message": "File contains .all() but no obvious pagination/limit hint.",
                }
            )
        if "for " in lower_content and any(token in lower_content for token in ("requests.", "fetch(", "session.execute", "await client", "storage")):
            findings.append(
                {
                    "type": "possible_repeated_io",
                    "severity": "med",
                    "file": filename,
                    "line": None,
                    "message": "File has loops plus DB/network/storage calls; verify batching and N+1 behavior.",
                }
            )
        if any(token in lower_content for token in ("read()", "read_bytes()", "json.loads")) and any(token in lower_content for token in ("upload", "file", "request")):
            findings.append(
                {
                    "type": "large_allocation_risk",
                    "severity": "low",
                    "file": filename,
                    "line": None,
                    "message": "Potential full-buffer read/allocation in request or file path; consider size limits or streaming.",
                }
            )

    return {"scanner": "performance_static", "scanned_files": scanned_files, "findings": findings}
