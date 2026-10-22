"""Bounded CSV/XLSX loading and compact profiles, without saving uploads."""
import csv
import datetime
import io
import re
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, BinaryIO

import numpy as np
import pandas as pd

import config

SUPPORTED_EXTENSIONS = ("csv", "xlsx")
_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}(?:[ T].+)?$")
_DATE_LIKE = re.compile(r"^\d{1,4}[-/]\d{1,2}[-/]\d{1,4}(?:[ T]\d{1,2}:\d{2}(?::\d{2}(?:\.\d+)?)?(?:Z|[+-]\d{2}:?\d{2})?)?$")
_LEADING_ZERO = re.compile(r"^[+-]?0\d+$")
_MAX_CELL_CHARS = 100_000


@dataclass
class DatasetProfile:
    filename: str
    df: pd.DataFrame
    text: str
    warnings: list[str] = field(default_factory=list)

    def to_prompt_text(self) -> str:
        return self.text


def _limit(name: str, default: int) -> int:
    return int(getattr(config, name, default))


def _clip(value: Any, limit: int = 120) -> str:
    text = str(value).replace("\r", " ").replace("\n", " ")
    return text if len(text) <= limit else text[:max(0, limit - 3)] + "..."


def _format_number(val: float | int, is_int: bool = False) -> str:
    if is_int and isinstance(val, (int, np.integer)):
        return str(val)
    if isinstance(val, (float, np.floating)):
        return "NaN" if np.isnan(val) else f"{val:.4g}"
    return str(val)


def _format_date(value: Any) -> str:
    if hasattr(value, "strftime"):
        if getattr(value, "hour", 0) or getattr(value, "minute", 0) or getattr(value, "second", 0):
            return value.strftime("%Y-%m-%d %H:%M:%S")
        return value.strftime("%Y-%m-%d")
    return str(value)


def _format_sample_val(value: Any) -> str:
    if pd.isna(value):
        return "NaN"
    if isinstance(value, (pd.Timestamp, datetime.datetime, datetime.date)):
        return _format_date(value)
    return _clip(value)


def _is_date_candidate(value: Any) -> bool:
    return bool(_DATE_LIKE.fullmatch(str(value).strip()))


def _detect_and_convert_dates(df: pd.DataFrame) -> list[str]:
    """Convert fully valid ISO columns only; preserve ambiguous or mixed text."""
    notices = []
    for col in df.columns:
        series = df[col]
        if pd.api.types.is_datetime64_any_dtype(series):
            continue
        if not (pd.api.types.is_object_dtype(series) or pd.api.types.is_string_dtype(series)):
            continue
        values = series.dropna().astype(str).str.strip()
        if values.empty or not values.map(_is_date_candidate).any():
            continue
        if not values.map(lambda value: bool(_ISO_DATE.fullmatch(value))).all():
            notices.append(f"Column '{_clip(col)}' contains mixed or ambiguous dates; its original text was preserved.")
            continue
        try:
            parsed = pd.to_datetime(series, format="ISO8601", errors="raise")
            if parsed.notna().sum() != series.notna().sum():
                raise ValueError("Date conversion lost values.")
            df[col] = parsed
        except (ValueError, TypeError, OverflowError):
            notices.append(f"Column '{_clip(col)}' has dates that could not be converted safely; its original text was preserved.")
    return notices


def _get_column_profile(series: pd.Series, col_name: str) -> str:
    missing_count = int(series.isna().sum())
    unique_count = int(series.nunique(dropna=True))
    non_null = series.dropna()
    details = []
    if pd.api.types.is_datetime64_any_dtype(series):
        clean_dtype = "datetime"
        if not non_null.empty:
            details.append(f"range {_format_date(non_null.min())} to {_format_date(non_null.max())}")
    elif pd.api.types.is_bool_dtype(series):
        clean_dtype = "bool"
    elif pd.api.types.is_numeric_dtype(series):
        is_int = pd.api.types.is_integer_dtype(series)
        clean_dtype = "int" if is_int else "float"
        if not non_null.empty:
            details.append(f"min {_format_number(non_null.min(), is_int)}, max {_format_number(non_null.max(), is_int)}, mean {non_null.mean():.4g}")
    else:
        clean_dtype = "string"
        if 0 < unique_count < 15:
            details.append("values: " + ", ".join(_clip(value, 80) for value in non_null.unique()))
    if missing_count:
        details.append(f"{missing_count} missing values")
    details.append(f"{unique_count} unique values")
    return f"- {_clip(col_name, 160)} ({clean_dtype}) — {', '.join(details)}"


def _read_source(source: str | Path | bytes | BinaryIO, filename: str | None) -> tuple[bytes, str]:
    max_bytes = _limit("MAX_UPLOAD_BYTES", 20 * 1024 * 1024)
    if isinstance(source, (str, Path)):
        path = Path(source)
        if not path.is_file():
            raise FileNotFoundError("Dataset file was not found. Check the selected path.")
        name = filename or path.name
        if path.stat().st_size > max_bytes:
            raise ValueError("The dataset exceeds the 20 MB upload limit.")
        with path.open("rb") as handle:
            payload = handle.read(max_bytes + 1)
    elif isinstance(source, (bytes, bytearray, memoryview)):
        name = filename
        if len(source) > max_bytes:
            raise ValueError("The dataset exceeds the 20 MB upload limit.")
        payload = bytes(source)
    elif hasattr(source, "read"):
        name = filename or getattr(source, "name", None)
        position = None
        try:
            position = source.tell()
            source.seek(0)
        except (AttributeError, OSError, io.UnsupportedOperation):
            pass
        try:
            payload = source.read(max_bytes + 1)
        finally:
            if position is not None:
                source.seek(position)
    else:
        raise ValueError("Select a CSV or XLSX dataset.")
    if not name:
        raise ValueError("A filename ending in .csv or .xlsx is required.")
    name = Path(str(name)).name
    if Path(name).suffix.lower().lstrip(".") not in SUPPORTED_EXTENSIONS:
        raise ValueError("Unsupported file format. Please select a CSV or XLSX file.")
    if not isinstance(payload, bytes):
        raise ValueError("Read the dataset as binary data, not as a text stream.")
    if len(payload) > max_bytes:
        raise ValueError("The dataset exceeds the 20 MB upload limit.")
    if not payload:
        raise ValueError("The selected file is empty. Choose a file containing a header and data rows.")
    return payload, name


def _read_csv(payload: bytes) -> tuple[pd.DataFrame, list[str]]:
    notices = []
    try:
        text = payload.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = payload.decode("latin1")
        notices.append("The CSV was read using Latin-1 encoding; check accented characters in the preview.")
    if "\x00" in text:
        raise ValueError("This does not look like a text CSV file. Choose a valid comma-separated CSV.")
    max_columns = _limit("MAX_DATASET_COLUMNS", 200)
    max_rows = _limit("MAX_DATASET_ROWS", 250_000)
    try:
        reader = csv.reader(io.StringIO(text, newline=""), strict=True)
        header = next((row for row in reader if row), None)
        if not header:
            raise ValueError("The CSV is empty. Include a header and at least one data row.")
        if len(header) > max_columns:
            raise ValueError(f"The dataset has too many columns; the limit is {max_columns}.")
        if any(not label.strip() for label in header) or len(set(header)) != len(header):
            raise ValueError("CSV column names must be non-empty and unique.")
        leading_zero_columns = set()
        row_count = 0
        for row in reader:
            if not row:
                continue
            row_count += 1
            if row_count > max_rows:
                raise ValueError(f"The dataset has too many rows; the limit is {max_rows:,}.")
            if len(row) != len(header):
                raise ValueError(f"CSV row near line {reader.line_num} has {len(row)} fields; expected {len(header)}. Check separators and quoting.")
            for index, cell in enumerate(row):
                if len(cell) > _MAX_CELL_CHARS:
                    raise ValueError(f"A CSV cell is too long; the limit is {_MAX_CELL_CHARS:,} characters.")
                if _LEADING_ZERO.fullmatch(cell.strip()):
                    leading_zero_columns.add(header[index])
        if not row_count:
            raise ValueError("The CSV contains a header but no data rows.")
    except csv.Error as exc:
        raise ValueError("The CSV could not be read. Check its quoting, separators, and cell lengths.") from exc
    dtypes = {name: "string" for name in leading_zero_columns}
    frame = pd.read_csv(io.StringIO(text), dtype=dtypes, nrows=max_rows + 1)
    if leading_zero_columns:
        notices.append("Leading-zero values were preserved as text in: " + ", ".join(_clip(name) for name in sorted(leading_zero_columns)))
    return frame, notices


def _read_xlsx(payload: bytes) -> pd.DataFrame:
    try:
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            if len(archive.infolist()) > 2000 or sum(item.file_size for item in archive.infolist()) > _limit("MAX_UPLOAD_BYTES", 20 * 1024 * 1024) * 5:
                raise ValueError("The workbook expands beyond the demo's processing limit. Export the required sheet as CSV.")
    except zipfile.BadZipFile as exc:
        raise ValueError("This is not a valid XLSX workbook. Open it in a spreadsheet editor and export it again.") from exc
    try:
        return pd.read_excel(io.BytesIO(payload), engine="openpyxl", nrows=_limit("MAX_DATASET_ROWS", 250_000) + 1)
    except (ValueError, KeyError, OSError, EOFError) as exc:
        raise ValueError("The XLSX workbook could not be read. Export its first sheet as CSV and try again.") from exc


def load_and_profile(source: str | Path | bytes | BinaryIO, filename: str | None = None) -> DatasetProfile:
    """Read a path or in-memory upload. Uploaded files are never persisted here."""
    payload, name = _read_source(source, filename)
    if Path(name).suffix.lower() == ".csv":
        try:
            df, notices = _read_csv(payload)
        except (pd.errors.ParserError, pd.errors.EmptyDataError) as exc:
            raise ValueError("The CSV could not be parsed. Check that it has a header and consistent comma-separated rows.") from exc
    else:
        df, notices = _read_xlsx(payload), []
    if df.empty or not len(df.columns):
        raise ValueError("The dataset contains no data rows. Choose a non-empty dataset.")
    if len(df.columns) > _limit("MAX_DATASET_COLUMNS", 200):
        raise ValueError(f"The dataset has too many columns; the limit is {_limit('MAX_DATASET_COLUMNS', 200)}.")
    if len(df) > _limit("MAX_DATASET_ROWS", 250_000):
        raise ValueError(f"The dataset has too many rows; the limit is {_limit('MAX_DATASET_ROWS', 250_000):,}.")
    notices.extend(_detect_and_convert_dates(df))
    lines = [f"Dataset: {_clip(name, 200)}", f"Rows: {len(df)}, Columns: {len(df.columns)}", "", "Columns:"]
    lines.extend(_get_column_profile(df[column], str(column)) for column in df.columns)
    if config.SAMPLE_ROWS > 0:
        lines.extend(["", "Sample rows:"])
        for _, row in df.head(min(config.SAMPLE_ROWS, 10)).iterrows():
            lines.append(", ".join(f"{_clip(column, 160)}={_format_sample_val(row[column])}" for column in df.columns))
    if notices:
        lines.extend(["", "Import notes:", *notices])
    profile_text = "\n".join(lines)
    max_profile = _limit("MAX_PROFILE_CHARS", 12_000)
    marker = "\n... [profile truncated; some column details or samples omitted]"
    if len(profile_text) > max_profile:
        profile_text = profile_text[:max(0, max_profile - len(marker))] + marker[:max_profile]
    return DatasetProfile(filename=name, df=df, text=profile_text, warnings=notices)
