from pathlib import Path
import pytest
from databuddy import DataBuddy
from executor import run_code

DEMO=Path(__file__).resolve().parents[1]/"examples"/"demo_sales.csv"


@pytest.mark.parametrize("code,expected", [
    ("result = df['sales'].sum()",["1000"]),
    ("result = df['sales'].mean()",["250"]),
    ("result = df['units'].sum()",["20"]),
    ("result = df.groupby('region')['sales'].sum()",["North", "400", "South", "600"]),
    ("result = df.groupby('product')['sales'].sum()",["Notebook", "Pen", "500"]),
    ("result = df.groupby(df['date'].dt.to_period('M'))['sales'].sum()",["2026-01", "300", "2026-02", "700"]),
    ("result = df['sales'].isna().sum()",["0"]),
])
def test_documented_demo_answers(code,expected):
    buddy=DataBuddy(DEMO)
    result=run_code(code,buddy.dataset.df)
    assert result.ok, result.error
    assert all(value in result.result_text for value in expected)


def test_new_runs_do_not_restore_state():
    first=DataBuddy(DEMO)
    first.conversation.add_turn("remember an example", "understood")
    second=DataBuddy(DEMO)
    assert second.conversation.recent_turns==[]
    assert second.conversation.last_analysis is None
