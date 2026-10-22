"""Disposable analysis worker with basic restrictions, not hardened isolation.

Only the trusted parent creates its pickle input. Outputs are bounded JSON.
This module deliberately does not import application configuration.
"""
import builtins
import contextlib
import io
import json
import pickle
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
from plotly.subplots import make_subplots

# -I excludes the script directory; load our dependency-free policy module.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from execution_policy import ALLOWED_IMPORTS, check_code

def _safe_import(name, globals=None, locals=None, fromlist=(), level=0):
    if level or name not in ALLOWED_IMPORTS:
        raise ImportError("This import is not supported in analysis code.")
    if any(part.startswith("_") or part == "*" for part in (fromlist or ())):
        raise ImportError("Private and wildcard imports are not supported.")
    return builtins.__import__(name, globals, locals, fromlist, level)

_SAFE_BUILTINS = {name: getattr(builtins, name) for name in (
    "abs", "all", "any", "bool", "dict", "enumerate", "filter", "float",
    "frozenset", "int", "isinstance", "len", "list", "map", "max", "min",
    "range", "repr", "reversed", "round", "set", "sorted", "str", "sum",
    "tuple", "zip", "Exception", "ValueError", "TypeError", "KeyError",
)}
_SAFE_BUILTINS["__import__"] = _safe_import

class _LimitedText(io.TextIOBase):
    """Discard bounded diagnostics without allowing print to corrupt JSON."""
    def __init__(self, limit):
        self.limit = limit
        self.count = 0
    def write(self, text):
        self.count += len(text.encode("utf-8"))
        if self.count > self.limit:
            raise ValueError("Printed output exceeded the allowed size.")
        return len(text)

def _format_result(value, max_rows: int, max_chars: int) -> str:
    if value is None:
        return "None"
    suffix = ""
    if isinstance(value, (pd.DataFrame, pd.Series)):
        if len(value) > max_rows:
            suffix = f"\n[showing {max_rows} of {len(value)} rows]"
        text = value.head(max_rows).to_string() + suffix
    else:
        text = str(value)
    marker = "... [truncated]"
    return text if len(text) <= max_chars else text[:max(0, max_chars-len(marker))] + marker

def _plain(value):
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)

def _chart_evidence(fig, max_rows, max_chars):
    """Describe actual plotted coordinates, not the model's interpretation."""
    traces = []
    for trace in list(fig.data)[:5]:
        evidence = {"type": trace.type, "name": trace.name}
        for field in ("x", "y", "values", "labels", "z"):
            values = getattr(trace, field, None)
            if values is None:
                continue
            arr = np.asarray(values)
            if arr.ndim == 0:
                continue
            flat = arr.ravel()
            evidence[field] = {"count": int(flat.size),
                               "sample": [_plain(v) for v in flat[:min(max_rows, 10)]]}
            if np.issubdtype(arr.dtype, np.number) and not np.iscomplexobj(arr):
                finite = flat[np.isfinite(flat)]
                if finite.size:
                    evidence[field].update(min=_plain(finite.min()), max=_plain(finite.max()))
        traces.append(evidence)
    text = "Actual plotted values (samples may be truncated):\n" + json.dumps(traces, ensure_ascii=True, default=str)
    return _format_result(text, max_rows, max_chars)

def _validate_chart_resources(fig):
    """The demo supports self-contained charts, not external maps or images."""
    remote_traces = {"scattermap", "scattermapbox", "choroplethmap", "choroplethmapbox",
                     "densitymap", "densitymapbox", "choropleth", "scattergeo"}
    for trace in fig.data:
        if trace.type in remote_traces:
            raise ValueError("Map charts requiring external resources are not supported in this demo.")
        source = getattr(trace, "source", None)
        if isinstance(source, str) and not source.startswith("data:image/"):
            raise ValueError("External chart image sources are not supported.")
    images = list(fig.layout.images or ())
    if fig.layout.template and fig.layout.template.layout:
        images.extend(fig.layout.template.layout.images or ())
    for image in images:
        source = image.source
        if source and not (isinstance(source, str) and source.startswith("data:image/")):
            raise ValueError("External chart image sources are not supported.")

def main() -> None:
    if len(sys.argv) != 8:
        print(json.dumps({"status": "error", "error": "Invalid worker arguments."}))
        return
    df_path, code_path = sys.argv[1:3]
    max_rows, max_chars, max_chart, max_output, max_code = map(int, sys.argv[3:])
    try:
        with open(df_path, "rb") as handle:
            df = pickle.load(handle)
        code = Path(code_path).read_text(encoding="utf-8")
        problem = check_code(code, max_code)
        if problem:
            raise ValueError(problem)
        diagnostics = _LimitedText(min(max_output, 16000))
        namespace = {"__builtins__": dict(_SAFE_BUILTINS), "df": df.copy(),
                     "pd": pd, "np": np, "px": px, "go": go,
                     "make_subplots": make_subplots}
        def safe_print(*args, **kwargs):
            if "file" in kwargs:
                raise ValueError("Printing to files is not supported.")
            builtins.print(*args, file=diagnostics, **kwargs)
        namespace["__builtins__"]["print"] = safe_print
        with contextlib.redirect_stdout(diagnostics), contextlib.redirect_stderr(diagnostics):
            exec(code, namespace)
        result = namespace.get("result")
        output = {"status": "ok", "result": _format_result(result, max_rows, max_chars)}
        fig = namespace.get("fig")
        if fig is not None:
            if not isinstance(fig, go.Figure):
                raise ValueError("The generated chart is not a Plotly figure.")
            _validate_chart_resources(fig)
            chart = pio.to_json(fig)
            if len(chart.encode("utf-8")) > max_chart:
                raise ValueError("Chart exceeds the size limit; aggregate or plot fewer points.")
            output["chart"] = chart
            output["chart_description"] = str(namespace.get("chart_description") or "Chart")[:300]
            if result is None:
                output["result"] = _chart_evidence(fig, max_rows, max_chars)
        encoded = json.dumps(output, ensure_ascii=True, allow_nan=False)
        if len(encoded.encode("utf-8")) > max_output:
            raise ValueError("Analysis output exceeded the allowed size.")
    except Exception as exc:
        encoded = json.dumps({"status": "error", "error": f"{type(exc).__name__}: {str(exc)[:700]}"}, ensure_ascii=True)
    sys.stdout.write(encoded + "\n")

if __name__ == "__main__":
    main()
