import datetime
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from config import SAMPLE_ROWS


@dataclass
class DatasetProfile:
    filename: str
    df: pd.DataFrame
    text: str

    def to_prompt_text(self) -> str:
        return self.text


def _format_number(val: float | int, is_int: bool = False) -> str:
    """Format numeric stats with consistent precision."""
    if is_int and isinstance(val, (int, np.integer)):
        return str(val)
    if isinstance(val, (float, np.floating)):
        if np.isnan(val):
            return "NaN"
        return f"{val:.2f}"
    return str(val)


def _format_date(d: Any) -> str:
    """Format date objects to ISO YYYY-MM-DD or datetime format."""
    if hasattr(d, "strftime"):
        if hasattr(d, "hour") and (d.hour != 0 or d.minute != 0 or d.second != 0):
            return d.strftime("%Y-%m-%d %H:%M:%S")
        return d.strftime("%Y-%m-%d")
    return str(d)


def _format_sample_val(val: Any) -> str:
    """Format a cell value for compact sample row representation."""
    if pd.isna(val):
        return "NaN"
    if isinstance(val, (pd.Timestamp, datetime.datetime, datetime.date)):
        return _format_date(val)
    return str(val)


def _is_date_candidate(val: Any) -> bool:
    """Heuristic check whether a string looks like a date/timestamp."""
    s = str(val).strip()
    sep_count = sum(1 for c in s if c in ("-", "/"))
    if sep_count >= 2:
        return True
    if sep_count == 1 and len(s) == 7:  # e.g. YYYY-MM
        return True
    return False


def _detect_and_convert_dates(df: pd.DataFrame) -> None:
    """Detect object/string columns that represent dates and convert them to datetime in-place."""
    for col in df.columns:
        series = df[col]
        if pd.api.types.is_datetime64_any_dtype(series):
            continue
        if pd.api.types.is_object_dtype(series) or pd.api.types.is_string_dtype(series):
            non_null = series.dropna()
            if len(non_null) == 0:
                continue

            sample = non_null.head(50)
            if all(_is_date_candidate(v) for v in sample.head(10)):
                try:
                    parsed = pd.to_datetime(sample, errors="coerce")
                    if parsed.notna().mean() >= 0.8:
                        df[col] = pd.to_datetime(df[col], errors="coerce")
                except Exception:
                    pass


def _get_column_profile(series: pd.Series, col_name: str) -> str:
    """Build the profile description line for a single column."""
    missing_count = int(series.isna().sum())
    unique_count = int(series.nunique(dropna=True))
    non_null = series.dropna()

    if pd.api.types.is_datetime64_any_dtype(series):
        clean_dtype = "datetime"
        details = []
        if len(non_null) > 0:
            min_date = non_null.min()
            max_date = non_null.max()
            details.append(f"range {_format_date(min_date)} to {_format_date(max_date)}")
        if missing_count > 0:
            details.append(f"{missing_count} missing values")

    elif pd.api.types.is_bool_dtype(series):
        clean_dtype = "bool"
        details = []
        if missing_count > 0:
            details.append(f"{missing_count} missing values")

    elif pd.api.types.is_numeric_dtype(series):
        is_int = pd.api.types.is_integer_dtype(series)
        clean_dtype = "int" if is_int else "float"
        details = []
        if len(non_null) > 0:
            col_min = non_null.min()
            col_max = non_null.max()
            col_mean = non_null.mean()
            details.append(
                f"min {_format_number(col_min, is_int)}, max {_format_number(col_max, is_int)}, mean {col_mean:.2f}"
            )
        if missing_count > 0:
            details.append(f"{missing_count} missing values")

    else:
        clean_dtype = "string"
        details = []
        unique_vals = non_null.unique()
        nunique = len(unique_vals)
        if 0 < nunique < 15:
            vals_str = ", ".join(str(v) for v in unique_vals)
            details.append(f"{nunique} unique values: {vals_str}")
        if missing_count > 0:
            details.append(f"{missing_count} missing values")

    details.append(f"{unique_count} unique values")
    if details:
        return f"- {col_name} ({clean_dtype}) — {', '.join(details)}"
    return f"- {col_name} ({clean_dtype})"


def load_and_profile(path: str) -> DatasetProfile:
    """Load a CSV or Excel file, build a compact text profile, and return a DatasetProfile."""
    path_obj = Path(path)
    if not path_obj.exists():
        raise FileNotFoundError(f"File not found: {path}")

    ext = path_obj.suffix.lower()
    if ext == ".csv":
        try:
            df = pd.read_csv(path)
        except UnicodeDecodeError:
            df = pd.read_csv(path, encoding="latin1")
    elif ext in (".xlsx", ".xls", ".xlsm", ".xlsb"):
        df = pd.read_excel(path)
    else:
        raise ValueError(f"Unsupported file format '{ext}'. Expected CSV or Excel file.")

    _detect_and_convert_dates(df)

    col_lines = [_get_column_profile(df[col], str(col)) for col in df.columns]

    sample_lines = []
    if len(df) > 0 and SAMPLE_ROWS > 0:
        sample_df = df.head(SAMPLE_ROWS)
        for _, row in sample_df.iterrows():
            row_str = ", ".join(f"{col}={_format_sample_val(row[col])}" for col in df.columns)
            sample_lines.append(row_str)

    profile_lines = [
        f"Dataset: {path_obj.name}",
        f"Rows: {len(df)}, Columns: {len(df.columns)}",
        "",
        "Columns:",
    ]
    profile_lines.extend(col_lines)

    if sample_lines:
        profile_lines.append("")
        profile_lines.append("Sample rows:")
        profile_lines.extend(sample_lines)

    profile_text = "\n".join(profile_lines)

    return DatasetProfile(
        filename=path_obj.name,
        df=df,
        text=profile_text,
    )
