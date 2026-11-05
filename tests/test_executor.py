"""Offline regression checks for trusted-demo execution behavior."""
import json
import os
from pathlib import Path
import tempfile
from unittest.mock import patch
import pandas as pd
import pytest
from backend.core import executor
from backend.core._runner import _format_result

@pytest.fixture
def frame():
    return pd.DataFrame({'region':['North','South','North'], 'sales':[10,20,30]})

@pytest.mark.parametrize('code,expected', [
    ("result = df['sales'].sum()", '60'),
    ("result = df['sales'].mean()", '20.0'),
    ("print('diagnostic'); result = len(df)", '3'),
    ("import numpy as np\nresult = np.mean(df['sales'])", '20.0'),
    ("from pandas import DataFrame\nresult = len(DataFrame({'x':[1,2]}))", '2'),
    ("result = 'हैलो café'", 'हैलो café'),
])
def test_analysis_and_allowed_imports(frame, code, expected):
    result = executor.run_code(code, frame)
    assert result.ok, result.error
    assert result.result_text == expected

@pytest.mark.parametrize('code', [
    "import os\nresult = 1", "result = pd.read_csv('private.csv')",
    "from pandas import read_csv as reader\nresult = reader('private.csv')",
    "df.to_csv('private.csv')", "result = np.load('private.npy')",
    "result = pd.io.common.os.environ", "result = df.__class__",
    "result = df._mgr", "result = getattr(pd, 'read_csv')('private.csv')",
    "from numpy import load as reader\nresult = reader('private.npy')",
    "result = df.to_string(buf='private.txt')", "result = pd.eval('1+1')",
    "result = df.to_string('private.txt')", "result = np.lib.format.open_memmap('private.npy')",
    "writer = df.to_string\nwriter('private.txt')\nresult = 1",
    "df.to_string(**{'buf':'private.txt'})\nresult = 1",
])
def test_obvious_io_and_private_operations_rejected(frame, code):
    with patch.object(executor, '_bounded_worker', side_effect=AssertionError('must not execute')):
        result = executor.run_code(code, frame)
    assert not result.ok
    assert 'Blocked' in result.error

@pytest.mark.parametrize('code', [
    "import plotly.express as px\nfig = px.bar(df, x='region', y='sales')",
    "from plotly.subplots import make_subplots\nfig = make_subplots()\nfig.add_trace(go.Bar(x=['a'], y=[42]))",
])
def test_chart_has_computed_evidence(frame, code):
    result = executor.run_code(code, frame)
    assert result.ok, result.error
    assert json.loads(result.chart_json)['data']
    assert 'Actual plotted values' in result.result_text
    assert 'sample' in result.result_text

@pytest.mark.parametrize('code', [
    "fig = go.Figure(go.Bar(x=['a'], y=[1])); fig.add_layout_image(source='https://example.com/image.png')",
    "fig = go.Figure(go.Scattergeo(lon=[0], lat=[0]))",
    "fig = go.Figure(go.Bar(x=['a'], y=[1])); fig.update_layout(template=go.layout.Template(layout=go.Layout(images=[dict(source='https://example.com/image.png')])) )",
])
def test_external_chart_resources_rejected(frame, code):
    result = executor.run_code(code, frame)
    assert not result.ok
    assert 'external' in result.error.lower()

def test_timeout(frame):
    with patch.object(executor, 'EXEC_TIMEOUT_SECONDS', 2):
        result = executor.run_code('while True: pass', frame)
    assert not result.ok
    assert 'timed out' in result.error

def test_chart_limit(frame):
    with patch.object(executor.config, 'MAX_CHART_BYTES', 100):
        result = executor.run_code("fig = px.bar(df, x='region', y='sales')", frame)
    assert not result.ok
    assert 'size limit' in result.error

def test_print_limit(frame):
    result = executor.run_code("print('x' * 20000); result = 1", frame)
    assert not result.ok
    assert 'Printed output' in result.error

def test_worker_environment_has_no_app_credentials(tmp_path):
    with patch.dict(os.environ, {'GROQ_API_KEY':'secret-sentinel', 'MISTRAL_API_KEY':'secret-sentinel',
                                 'DATABASE_URL':'secret-sentinel', 'PYTHONPATH':'private-directory'}):
        env = executor._worker_environment(str(tmp_path))
    assert not {'GROQ_API_KEY','MISTRAL_API_KEY','DATABASE_URL','PYTHONPATH'} & env.keys()
    assert env['HOME'] == str(tmp_path)
    assert env['TEMP'] == str(tmp_path)

def test_temp_files_cleaned_on_success_and_failure(frame):
    real = tempfile.TemporaryDirectory
    created = []
    def tracked(*args, **kwargs):
        directory = real(*args, **kwargs)
        created.append(Path(directory.name))
        return directory
    with patch.object(executor.tempfile, 'TemporaryDirectory', side_effect=tracked):
        assert executor.run_code('result = 1', frame).ok
        assert not executor.run_code('result = 1 / 0', frame).ok
    assert created
    assert not any(path.exists() for path in created)

def test_parent_does_not_accept_non_json_worker_output(frame):
    with patch.object(executor, '_bounded_worker', return_value=(0,b'not json',False)):
        result = executor.run_code('result = 1', frame)
    assert not result.ok
    assert 'invalid result' in result.error

def test_code_and_worker_output_limits(frame):
    with patch.object(executor.config, 'MAX_CODE_CHARS', 5):
        assert not executor.run_code('result = 123', frame).ok
    with patch.object(executor, '_bounded_worker', return_value=(0,b'',True)):
        result = executor.run_code('result = 1', frame)
    assert not result.ok
    assert 'output exceeded' in result.error

def test_result_truncation_reports_rows():
    result = _format_result(pd.DataFrame({'x':range(100)}), 3, 500)
    assert '[showing 3 of 100 rows]' in result
    assert len(_format_result('x'*1000, 3, 40)) <= 40

def test_input_frame_not_mutated(frame):
    result = executor.run_code("df['sales'] = 0\nresult = df['sales'].sum()", frame)
    assert result.ok
    assert frame['sales'].sum() == 60
