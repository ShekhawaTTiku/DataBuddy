import ast
import json
import os
import pickle
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from config import EXEC_TIMEOUT_SECONDS, MAX_RESULT_CHARS, MAX_RESULT_ROWS

# ---------------------------------------------------------------------------
# Dataclass for execution results
# ---------------------------------------------------------------------------


@dataclass
class ExecutionResult:
    ok: bool
    result_text: str | None
    error: str | None
    chart_json: str | None = None
    chart_description: str | None = None


# ---------------------------------------------------------------------------
# Static safety check (AST-based)
# ---------------------------------------------------------------------------

_FORBIDDEN_NAMES = {
    "open", "exec", "eval", "compile", "__import__",
    "input", "exit", "quit", "breakpoint",
}

_FORBIDDEN_MODULES = {
    "os", "sys", "subprocess", "shutil", "pathlib",
    "socket", "http", "urllib", "requests",
    "ctypes", "importlib", "signal", "threading",
    "multiprocessing", "webbrowser", "ftplib",
    "smtplib", "telnetlib", "xmlrpc",
}


def _static_check(code: str) -> str | None:
    """Parse code with ast and return an error message if unsafe, or None if ok."""
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return f"SyntaxError: {e.msg} (line {e.lineno})"

    for node in ast.walk(tree):
        # --- Imports ---
        if isinstance(node, ast.Import):
            for alias in node.names:
                top = alias.name.split(".")[0]
                if top not in ("pandas", "numpy", "pd", "np", "plotly"):
                    return f"Blocked import: '{alias.name}' is not allowed."

        if isinstance(node, ast.ImportFrom):
            if node.module is not None:
                top = node.module.split(".")[0]
                if top not in ("pandas", "numpy", "pd", "np", "plotly"):
                    return f"Blocked import: 'from {node.module}' is not allowed."

        # --- Forbidden function calls by name ---
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name) and func.id in _FORBIDDEN_NAMES:
                return f"Blocked call: '{func.id}()' is not allowed."
            if isinstance(func, ast.Attribute) and func.attr in _FORBIDDEN_NAMES:
                return f"Blocked call: '.{func.attr}()' is not allowed."

        # --- Forbidden bare names (e.g. referencing `os` without calling) ---
        if isinstance(node, ast.Name) and node.id in _FORBIDDEN_MODULES:
            return f"Blocked reference: '{node.id}' is not allowed."

        # --- Forbidden attribute references to blocked modules ---
        if isinstance(node, ast.Attribute):
            if isinstance(node.value, ast.Name) and node.value.id in _FORBIDDEN_MODULES:
                return f"Blocked reference: '{node.value.id}.{node.attr}' is not allowed."

        # --- Dunder attribute access ---
        if isinstance(node, ast.Attribute):
            if node.attr.startswith("__") and node.attr.endswith("__"):
                return f"Blocked attribute: dunder access '.{node.attr}' is not allowed."

    return None


# ---------------------------------------------------------------------------
# Runner path
# ---------------------------------------------------------------------------

_RUNNER_PATH = Path(__file__).parent / "_runner.py"


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------


def run_code(code: str, df: pd.DataFrame) -> ExecutionResult:
    """Run LLM-generated code safely and return the result.

    1. Static AST check — reject unsafe code before running.
    2. Pickle the DataFrame and write code to tempfiles.
    3. Invoke _runner.py in a child subprocess via sys.executable.
    4. Enforce a hard timeout; parse the JSON result from stdout.
    """
    # Step 1: Static safety check
    safety_error = _static_check(code)
    if safety_error is not None:
        return ExecutionResult(ok=False, result_text=None, error=safety_error)

    df_path = code_path = None
    try:
        # Step 2: Write DataFrame and code to temp files
        with tempfile.NamedTemporaryFile(suffix=".pkl", delete=False) as fh:
            pickle.dump(df, fh)
            df_path = fh.name

        with tempfile.NamedTemporaryFile(suffix=".py", mode="w",
                                         encoding="utf-8", delete=False) as fh:
            fh.write(code)
            code_path = fh.name

        # Step 3: Run runner in a child process with a hard timeout
        proc = subprocess.run(
            [sys.executable, str(_RUNNER_PATH),
             df_path, code_path,
             str(MAX_RESULT_ROWS), str(MAX_RESULT_CHARS)],
            capture_output=True,
            text=True,
            timeout=EXEC_TIMEOUT_SECONDS,
        )

        # Step 4: Parse the JSON output written by the runner
        stdout = proc.stdout.strip()
        if not stdout:
            stderr_hint = proc.stderr.strip()
            return ExecutionResult(
                ok=False, result_text=None,
                error=f"Runner produced no output.{' stderr: ' + stderr_hint if stderr_hint else ''}",
            )

        data = json.loads(stdout)
        if data.get("status") == "ok":
            return ExecutionResult(
                ok=True,
                result_text=data["result"],
                error=None,
                chart_json=data.get("chart"),
                chart_description=data.get("chart_description"),
            )
        else:
            return ExecutionResult(ok=False, result_text=None, error=data.get("error", "Unknown runner error."))

    except subprocess.TimeoutExpired:
        return ExecutionResult(
            ok=False, result_text=None,
            error=f"Execution timed out after {EXEC_TIMEOUT_SECONDS} seconds.",
        )
    except json.JSONDecodeError as exc:
        return ExecutionResult(ok=False, result_text=None, error=f"Runner output was not valid JSON: {exc}")
    except Exception as exc:
        return ExecutionResult(ok=False, result_text=None, error=f"Executor error: {type(exc).__name__}: {exc}")
    finally:
        # Step 5: Always clean up temp files
        for path in (df_path, code_path):
            if path:
                try:
                    os.unlink(path)
                except OSError:
                    pass
