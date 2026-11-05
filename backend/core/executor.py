"""Time- and output-bounded execution for trusted demonstrations.

Checks reduce accidental unsafe behavior; they are not hardened isolation
for arbitrary public code execution.
"""
import json
import os
import pickle
import subprocess
import sys
import tempfile
import threading
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from backend.core import config
from backend.core import response_stream
import time
from backend.core.execution_policy import check_code

@dataclass
class ExecutionResult:
    ok: bool
    result_text: str | None
    error: str | None
    chart_json: str | None = None
    chart_description: str | None = None
    result_table: dict | None = None

_RUNNER_PATH = Path(__file__).with_name("_runner.py")
EXEC_TIMEOUT_SECONDS = config.EXEC_TIMEOUT_SECONDS
MAX_RESULT_CHARS = config.MAX_RESULT_CHARS
MAX_RESULT_ROWS = config.MAX_RESULT_ROWS

def _static_check(code: str) -> str | None:
    return check_code(code, getattr(config, "MAX_CODE_CHARS", 16000))

def _worker_environment(folder: str) -> dict[str, str]:
    """Pass only runtime essentials, never the application's API keys."""
    allowed = ("SYSTEMROOT", "WINDIR", "PATH", "LD_LIBRARY_PATH")
    env = {key: os.environ[key] for key in allowed if key in os.environ}
    env.update({"TEMP": folder, "TMP": folder, "TMPDIR": folder,
                "HOME": folder, "USERPROFILE": folder,
                "OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1"})
    return env

def _bounded_worker(args: list[str], folder: str) -> tuple[int, bytes, bool]:
    """Read both pipes with an aggregate byte limit, then reap the child."""
    limit = getattr(config, "MAX_WORKER_OUTPUT_BYTES", 1500000)
    chunks: list[bytes] = []
    total = 0
    exceeded = threading.Event()
    lock = threading.Lock()
    proc = subprocess.Popen(args, cwd=folder, env=_worker_environment(folder),
                            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)
    def consume(pipe, keep):
        nonlocal total
        try:
            while block := pipe.read(4096):
                with lock:
                    total += len(block)
                    if total > limit:
                        exceeded.set()
                    elif keep:
                        chunks.append(block)
                if exceeded.is_set():
                    try:
                        proc.kill()
                    except OSError:
                        pass  # Another reader or the worker may already have stopped it.
                    break
        finally:
            pipe.close()
    readers = [threading.Thread(target=consume, args=(proc.stdout, True), daemon=True),
               threading.Thread(target=consume, args=(proc.stderr, False), daemon=True)]
    for reader in readers:
        reader.start()
    try:
        deadline = time.monotonic() + EXEC_TIMEOUT_SECONDS
        while proc.poll() is None:
            response_stream.check_cancelled()
            if time.monotonic() >= deadline:
                raise subprocess.TimeoutExpired(args, EXEC_TIMEOUT_SECONDS)
            try:
                proc.wait(timeout=min(.1, max(.001, deadline - time.monotonic())))
            except subprocess.TimeoutExpired:
                pass
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()
        raise
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait()
        for reader in readers:
            reader.join(timeout=2)
    return proc.returncode, b"".join(chunks), exceeded.is_set()

def run_code(code: str, df: pd.DataFrame) -> ExecutionResult:
    """Run validated code in a disposable worker; return validated JSON only."""
    problem = _static_check(code)
    if problem:
        return ExecutionResult(False, None, problem)
    try:
        with tempfile.TemporaryDirectory(prefix="databuddy_run_") as folder:
            df_path = Path(folder) / "dataset.pkl"
            code_path = Path(folder) / "analysis.py"
            # Trusted parent-created input; user pickle uploads are never accepted.
            with df_path.open("wb") as handle:
                pickle.dump(df, handle, protocol=pickle.HIGHEST_PROTOCOL)
            code_path.write_text(code, encoding="utf-8")
            args = [sys.executable, "-I", str(_RUNNER_PATH), str(df_path), str(code_path),
                    str(MAX_RESULT_ROWS), str(MAX_RESULT_CHARS),
                    str(getattr(config, "MAX_CHART_BYTES", 1000000)),
                    str(getattr(config, "MAX_WORKER_OUTPUT_BYTES", 1500000)),
                    str(getattr(config, "MAX_CODE_CHARS", 16000))]
            returncode, output, exceeded = _bounded_worker(args, folder)
            if exceeded:
                return ExecutionResult(False, None, "Analysis output exceeded the allowed size.")
            if not output.strip():
                return ExecutionResult(False, None, "The analysis worker stopped without a result.")
            data = json.loads(output.decode("utf-8"))
            if not isinstance(data, dict) or data.get("status") not in {"ok", "error"}:
                raise ValueError("Invalid result structure")
            if data["status"] == "error":
                return ExecutionResult(False, None, str(data.get("error", "Analysis failed."))[:1000])
            if returncode != 0 or not isinstance(data.get("result"), str):
                raise ValueError("Worker did not complete successfully")
            chart = data.get("chart")
            if chart is not None and (not isinstance(chart, str) or
                    len(chart.encode("utf-8")) > getattr(config, "MAX_CHART_BYTES", 1000000)):
                raise ValueError("Chart is too large")
            description = data.get("chart_description")
            if description is not None and not isinstance(description, str):
                raise ValueError("Invalid chart description")
            return ExecutionResult(True, data["result"][:MAX_RESULT_CHARS], None,
                                   chart, description[:300] if description else None, data.get("table"))
    except subprocess.TimeoutExpired:
        return ExecutionResult(False, None, f"Execution timed out after {EXEC_TIMEOUT_SECONDS} seconds.")
    except (json.JSONDecodeError, UnicodeDecodeError, ValueError):
        return ExecutionResult(False, None, "The analysis worker returned an invalid result.")
    except response_stream.ResponseCancelled:
        raise
    except Exception:
        return ExecutionResult(False, None, "The analysis could not run. Please try a simpler question.")
