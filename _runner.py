"""Sandboxed code runner — invoked as a child subprocess by executor.py.

Called as:
    python _runner.py <df_pickle_path> <code_path> <max_rows> <max_chars>

Prints a single JSON line to stdout:
    {"status": "ok",    "result": "<formatted result>"}
    {"status": "error", "error":  "<error message>"}
"""
import sys
import json
import math
import pickle

import pandas as pd
import numpy as np

try:
    import plotly.express as px
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    import plotly.io as pio
    _PLOTLY_AVAILABLE = True
except ImportError:
    px = go = make_subplots = pio = None
    _PLOTLY_AVAILABLE = False

# ---------------------------------------------------------------------------
# Safe builtins whitelist (mirror of executor.py — kept in sync manually)
# ---------------------------------------------------------------------------

_SAFE_BUILTINS = {
    "abs": abs,
    "all": all,
    "any": any,
    "bool": bool,
    "dict": dict,
    "enumerate": enumerate,
    "filter": filter,
    "float": float,
    "frozenset": frozenset,
    "int": int,
    "isinstance": isinstance,
    "len": len,
    "list": list,
    "map": map,
    "max": max,
    "min": min,
    "print": print,
    "range": range,
    "repr": repr,
    "reversed": reversed,
    "round": round,
    "set": set,
    "sorted": sorted,
    "str": str,
    "sum": sum,
    "tuple": tuple,
    "type": type,
    "zip": zip,
    "True": True,
    "False": False,
    "None": None,
}


def _format_result(value, max_rows: int, max_chars: int) -> str:
    """Convert the result variable to compact text."""
    if value is None:
        return "None"

    if isinstance(value, float):
        if not math.isnan(value):
            value = round(value, 4)
        return str(value)

    if isinstance(value, (pd.DataFrame, pd.Series)):
        if isinstance(value, pd.DataFrame) and len(value) > max_rows:
            value = value.head(max_rows)
        elif isinstance(value, pd.Series) and len(value) > max_rows:
            value = value.head(max_rows)
        text = str(value)
    else:
        text = str(value)

    if len(text) > max_chars:
        text = text[:max_chars] + "... [truncated]"

    return text


def main() -> None:
    if len(sys.argv) < 5:
        print(json.dumps({"status": "error", "error": "Runner called with wrong arguments."}))
        sys.exit(1)

    df_path   = sys.argv[1]
    code_path = sys.argv[2]
    max_rows  = int(sys.argv[3])
    max_chars = int(sys.argv[4])

    try:
        with open(df_path, "rb") as fh:
            df = pickle.load(fh)
    except Exception as exc:
        print(json.dumps({"status": "error", "error": f"Failed to load DataFrame: {exc}"}))
        sys.exit(1)

    try:
        with open(code_path, "r", encoding="utf-8") as fh:
            code = fh.read()
    except Exception as exc:
        print(json.dumps({"status": "error", "error": f"Failed to read code file: {exc}"}))
        sys.exit(1)

    namespace = {
        "__builtins__": _SAFE_BUILTINS,
        "df": df.copy(),
        "pd": pd,
        "np": np,
    }

    # Add plotly to namespace if available
    if _PLOTLY_AVAILABLE:
        namespace["px"] = px
        namespace["go"] = go
        namespace["make_subplots"] = make_subplots

    try:
        exec(code, namespace)  # noqa: S102
        result_value = namespace.get("result", None)
        result_text  = _format_result(result_value, max_rows, max_chars)

        # Detect and serialize Plotly figure if present
        fig_value = namespace.get("fig", None)
        chart_json = None
        chart_description = namespace.get("chart_description", None)

        if fig_value is not None and _PLOTLY_AVAILABLE:
            try:
                chart_json = pio.to_json(fig_value)
            except Exception:
                pass  # If serialization fails, just skip the chart

        output = {"status": "ok", "result": result_text}
        if chart_json:
            output["chart"] = chart_json
        if chart_description:
            output["chart_description"] = str(chart_description)
        print(json.dumps(output))
    except Exception as exc:
        print(json.dumps({"status": "error", "error": f"{type(exc).__name__}: {exc}"}))


if __name__ == "__main__":
    main()
