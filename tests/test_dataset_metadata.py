"""Offline, value-free suggestion metadata and lifecycle regressions."""
import pandas as pd

from api.dataset_metadata import suggestion_columns


def test_column_kinds_identifiers_counts_and_no_values():
    frame = pd.DataFrame({
        "OrderDate": pd.to_datetime(["2026-01-01", "2026-01-02", None]),
        "CustomerID": [101, 102, 103],
        "Sales": [10.5, None, 30.5],
        "Region": ["SYNTHETIC_VALUE_A", "SYNTHETIC_VALUE_B", "SYNTHETIC_VALUE_A"],
        "Enabled": [True, False, True],
        "Constant": [1, 1, 1],
        "Ambiguous Date": ["01/02/26", "02/03/26", None],
        "Empty": [None, None, None],
    })
    result = {item["name"]: item for item in suggestion_columns(frame)}
    assert result["OrderDate"]["kind"] == "date"
    assert result["CustomerID"]["identifier"] is True
    assert result["Sales"] == {"name": "Sales", "kind": "number", "distinct": 2, "missing": 1, "identifier": False}
    assert result["Region"]["kind"] == result["Enabled"]["kind"] == "category"
    assert result["Constant"]["distinct"] == 1
    assert result["Empty"]["distinct"] == 0 and result["Empty"]["missing"] == 3
    assert result["Ambiguous Date"]["kind"] == "text"
    assert "SYNTHETIC_VALUE" not in str(result)


def test_free_text_is_not_offered_as_groups_and_frame_is_unchanged():
    frame = pd.DataFrame({"Notes": [f"Synthetic note {i}" for i in range(60)], "Postal Code": range(60)})
    before = frame.copy(deep=True)
    result = suggestion_columns(frame)
    assert result[0]["kind"] == "text"
    assert result[1]["identifier"] is True
    pd.testing.assert_frame_equal(frame, before)
