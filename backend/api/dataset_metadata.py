"""Session-only column facts for local UI suggestions; never include cell values."""
import re

import pandas as pd


def suggestion_columns(frame: pd.DataFrame) -> list[dict]:
    columns = []
    for name in frame.columns:
        series = frame[name]
        label = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", str(name)).casefold()
        words = set(re.findall(r"[a-z0-9]+", label))
        identifier = bool(words & {"id", "uuid", "guid", "identifier", "index", "zip", "postcode"})
        identifier |= bool({"postal", "code"} <= words or {"row", "number"} <= words)
        distinct = int(series.nunique(dropna=True))
        if pd.api.types.is_datetime64_any_dtype(series):
            kind = "date"
        elif pd.api.types.is_bool_dtype(series):
            kind = "category"
        elif pd.api.types.is_numeric_dtype(series):
            kind = "number"
        elif distinct > 50 or words & {"date", "timestamp", "datetime"}:
            # Ambiguous date-like strings stay text, matching the loader's policy.
            kind = "text"
        else:
            kind = "category"
        columns.append({"name": str(name), "kind": kind, "distinct": distinct,
                        "missing": int(series.isna().sum()), "identifier": identifier})
    return columns
