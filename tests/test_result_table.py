import pandas as pd
from backend.core.executor import run_code


def test_period_index_table_keeps_calculation_and_bounded_cells():
    df = pd.DataFrame({'date': pd.to_datetime(['2026-01-01', '2026-02-01']), 'sales': [300, 700]})
    result = run_code("result = df.groupby(df['date'].dt.to_period('M'))['sales'].sum()", df)
    assert result.ok
    assert result.result_table['index'] == ['2026-01', '2026-02']
    assert result.result_table['rows'] == [[300], [700]]


def test_result_table_normalizes_nulls_and_caps_cells():
    df = pd.DataFrame({'text': ['a' * 1000, None], 'value': [float('inf'), float('nan')]})
    result = run_code('result = df', df)
    assert result.ok
    assert len(result.result_table['rows'][0][0]) == 240
    assert result.result_table['rows'][0][1] is None
