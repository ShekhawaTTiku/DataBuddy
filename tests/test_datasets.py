"""Dataset regression checks use synthetic local data and no provider APIs."""
import io
import zipfile

import pandas as pd
import pytest

from backend.core import config
from backend.core.dataset_profiler import load_and_profile


def test_csv_values_and_leading_zero_identifiers_are_preserved():
    profile = load_and_profile(b"id,region,sales\n001,North,10\n002,South,20\n003,North,30\n", "demo.csv")
    assert profile.df["id"].tolist() == ["001", "002", "003"]
    assert profile.df.groupby("region")["sales"].sum().to_dict() == {"North": 40, "South": 20}
    assert profile.df["sales"].mean() == 20
    assert profile.warnings


def test_path_and_binary_upload_inputs(tmp_path):
    content = b"name,value\na,1\nb,2\n"
    source = tmp_path / "sample.csv"
    source.write_bytes(content)
    assert load_and_profile(source).df["value"].sum() == 3
    stream = io.BytesIO(content)
    stream.seek(3)
    assert load_and_profile(stream, filename="sample.csv").df["value"].sum() == 3
    assert stream.tell() == 3
    assert sorted(path.name for path in tmp_path.iterdir()) == ["sample.csv"]


@pytest.mark.parametrize("content", [b"", b"\n\n", b"name,value\n", b"name,value\n\n"])
def test_empty_or_header_only_files_are_rejected(content):
    with pytest.raises(ValueError, match="empty|no data rows"):
        load_and_profile(content, "empty.csv")


@pytest.mark.parametrize("content", [b"a,b\n1,2,3\n", b"a,b\n1\n", b'a,b\n"unfinished,2\n', b"a,a\n1,2\n", b",b\n1,2\n"])
def test_malformed_csv_is_rejected(content):
    with pytest.raises(ValueError):
        load_and_profile(content, "bad.csv")


def test_full_column_validation_prevents_date_loss():
    content = "date,value\n" + "2025-01-01,1\n" * 60 + "not-a-date,2\n"
    profile = load_and_profile(content.encode(), "dates.csv")
    assert str(profile.df["date"].dtype) != "datetime64[ns]"
    assert profile.df["date"].iloc[-1] == "not-a-date"
    assert profile.df["date"].notna().all()
    assert profile.warnings


@pytest.mark.parametrize("date", ["31/12/2025", "01/02/2025", "2025-02-30"])
def test_mixed_ambiguous_and_invalid_dates_stay_text(date):
    profile = load_and_profile(f"date,value\n2025-01-01,1\n{date},2\n".encode(), "dates.csv")
    assert profile.df["date"].iloc[-1] == date
    assert profile.df["date"].notna().all()
    assert profile.warnings


def test_valid_iso_dates_are_converted():
    profile = load_and_profile(b"date,value\n2025-01-01,1\n2025-02-01,2\n", "dates.csv")
    assert pd.api.types.is_datetime64_any_dtype(profile.df["date"])


def test_product_dimensions_are_not_reported_as_ambiguous_dates():
    profile = load_and_profile(b"Product Name\n3-1/2 inch synthetic binder\nOffice notebook\n", "products.csv")
    assert not any("ambiguous dates" in warning for warning in profile.warnings)
    assert profile.df["Product Name"].iloc[0] == "3-1/2 inch synthetic binder"
    assert not profile.warnings


def test_missing_numeric_values_remain_missing():
    profile = load_and_profile(b"group,value\na,10\nb,\nc,30\n", "missing.csv")
    assert profile.df["value"].isna().sum() == 1
    assert profile.df["value"].sum() == 40


def test_size_limit_applies_to_bytes_streams_and_paths(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "MAX_UPLOAD_BYTES", 10, raising=False)
    data = b"a,b\n12345,2\n"
    path = tmp_path / "size.csv"
    path.write_bytes(data)
    for source in [data, io.BytesIO(data), path]:
        with pytest.raises(ValueError, match="20 MB"):
            load_and_profile(source, "size.csv")


def test_row_and_column_limits(monkeypatch):
    monkeypatch.setattr(config, "MAX_DATASET_ROWS", 1, raising=False)
    with pytest.raises(ValueError, match="too many rows"):
        load_and_profile(b"a,b\n1,2\n3,4\n", "rows.csv")
    monkeypatch.setattr(config, "MAX_DATASET_COLUMNS", 1, raising=False)
    with pytest.raises(ValueError, match="too many columns"):
        load_and_profile(b"a,b\n1,2\n", "columns.csv")


def test_profile_length_is_bounded(monkeypatch):
    monkeypatch.setattr(config, "MAX_PROFILE_CHARS", 180, raising=False)
    profile = load_and_profile(("text,value\n" + "a" * 2000 + ",10\n").encode(), "long.csv")
    assert len(profile.text) <= 180
    assert "truncated" in profile.text
    assert len(profile.df["text"].iloc[0]) == 2000


def test_xlsx_in_memory_and_unsupported_formats():
    data = io.BytesIO()
    pd.DataFrame({"region": ["North", "South"], "sales": [10, 20]}).to_excel(data, index=False)
    profile = load_and_profile(data.getvalue(), "sample.xlsx")
    assert profile.df["sales"].sum() == 30
    for filename in ["old.xls", "binary.xlsb", "macro.xlsm", "script.py"]:
        with pytest.raises(ValueError, match="Unsupported"):
            load_and_profile(data.getvalue(), filename)


def test_xlsx_corruption_and_expansion_are_rejected(monkeypatch):
    with pytest.raises(ValueError, match="valid XLSX"):
        load_and_profile(b"not-a-workbook", "bad.xlsx")
    content = io.BytesIO()
    with zipfile.ZipFile(content, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("huge.xml", "0" * 100_000)
    monkeypatch.setattr(config, "MAX_UPLOAD_BYTES", 1000, raising=False)
    with pytest.raises(ValueError, match="expands"):
        load_and_profile(content.getvalue(), "large.xlsx")
