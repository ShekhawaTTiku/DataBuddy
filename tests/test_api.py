import io
import threading
import time
from types import SimpleNamespace

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from api import main
from databuddy import DataBuddy, AskResult
import telemetry
import llm_clients


class FakeBuddy(DataBuddy):
    count = 0
    total = 1000
    wait = None
    def ask(self, question):
        type(self).count += 1
        if type(self).wait:
            type(self).wait.wait(3)
        telemetry.stage("Running calculation")
        telemetry.event("attempt", provider="Fixture")
        response = SimpleNamespace(usage=SimpleNamespace(prompt_tokens=self.total - 100, completion_tokens=100, total_tokens=self.total))
        telemetry.record_usage(response, "Fixture", "offline-model")
        return AskResult("Computed total: 1000", result_text="1000", code="result = df['Sales'].sum()")


@pytest.fixture
def client():
    FakeBuddy.count, FakeBuddy.total, FakeBuddy.wait = 0, 1000, None
    with TestClient(main.create_app(FakeBuddy)) as c:
        yield c


def new(client):
    response = client.post('/api/session')
    assert response.status_code == 201
    return {"Authorization": "Bearer " + response.json()["token"]}


def ready(client, headers):
    assert client.post('/api/sample', headers=headers).status_code == 200


def ask(client, headers, key='a' * 16):
    return client.post('/api/messages', headers=headers, json={"question": "Total sales?", "request_id": key})


def wait(client, headers):
    for _ in range(300):
        data = client.get('/api/session', headers=headers).json()
        if not data.get('job') or data['job']['state'] == 'done':
            return data
        time.sleep(.01)
    raise AssertionError('Job did not complete')


def test_isolation_authentication_cors_and_no_store(client):
    one, two = new(client), new(client)
    ready(client, one)
    assert client.get('/api/session', headers=two).json()['dataset'] is None
    assert client.get('/api/session').status_code == 401
    assert client.get('/api/job').status_code == 401
    assert client.get('/api/session', headers={'Authorization': 'Bearer wrong'}).status_code == 401
    assert client.get('/api/health').headers['cache-control'] == 'no-store'
    assert client.post('/api/session', headers={'Origin': 'https://untrusted.example'}).status_code == 403
    allowed = client.options('/api/session', headers={'Origin': 'http://localhost:5173', 'Access-Control-Request-Method': 'GET', 'Access-Control-Request-Headers': 'Authorization'})
    assert allowed.headers['access-control-allow-origin'] == 'http://localhost:5173'


def test_sample_preview_and_real_csv_xlsx_upload(client):
    h = new(client)
    ready(client, h)
    d = client.get('/api/session', headers=h).json()['dataset']
    assert d['rows'] == 4 and d['numeric'] == ['Sales', 'Units']
    response = client.put('/api/dataset', headers={**h, 'X-Filename': 'test.csv'}, content=b'value\n4\n9\n')
    assert response.json()['dataset']['preview'] == [[4], [9]]
    excel = io.BytesIO()
    pd.DataFrame({'value': [7, 8]}).to_excel(excel, index=False)
    response = client.put('/api/dataset', headers={**h, 'X-Filename': 'test.xlsx'}, content=excel.getvalue())
    assert response.json()['dataset']['preview'] == [[7], [8]]


def test_suggestion_metadata_is_cached_and_follows_dataset_lifecycle(client, monkeypatch):
    original = main.suggestion_columns
    calls = []
    def describe(frame):
        calls.append(True)
        return original(frame)
    monkeypatch.setattr(main, 'suggestion_columns', describe)
    h = new(client)
    response = client.post('/api/sample', headers=h).json()
    columns = response['dataset']['suggestion_columns']
    assert {c['name']: c['kind'] for c in columns} == {
        'Month': 'date', 'Region': 'category', 'Product': 'category', 'Sales': 'number', 'Units': 'number'}
    assert response['usage']['used'] == 0
    assert client.get('/api/session', headers=h).json()['dataset']['suggestion_columns'] == columns
    assert client.post('/api/reset', headers=h).json()['dataset']['suggestion_columns'] == columns
    assert len(calls) == 1
    assert client.put('/api/dataset', headers={**h, 'X-Filename': 'bad.csv'}, content=b'a,b\n1\n').status_code == 422
    assert client.get('/api/session', headers=h).json()['dataset']['suggestion_columns'] == columns
    changed = client.put('/api/dataset', headers={**h, 'X-Filename': 'new.csv'}, content=b'Score\n4\n8\n').json()
    assert [column['name'] for column in changed['dataset']['suggestion_columns']] == ['Score']
    assert len(calls) == 2
    assert client.delete('/api/dataset', headers=h).json()['dataset'] is None
    assert client.app.state.sessions[h['Authorization'].split()[1]].suggestion_columns == []


def test_invalid_upload_keeps_previous_dataset_and_releases_gate(client, monkeypatch):
    h = new(client); ready(client, h)
    bad = client.put('/api/dataset', headers={**h, 'X-Filename': 'invalid.csv'}, content=b'one,two\n1\n')
    assert bad.status_code == 422
    assert client.get('/api/session', headers=h).json()['dataset']['rows'] == 4
    assert client.put('/api/dataset', headers={**h, 'X-Filename': 'bad.exe'}, content=b'x').status_code == 422
    monkeypatch.setattr(main.config, 'MAX_UPLOAD_BYTES', 10)
    assert client.put('/api/dataset', headers={**h, 'X-Filename': 'large.csv'}, content=b'x' * 11).status_code == 413
    assert ask(client, h).status_code == 202


def test_idempotent_submission_rejects_conflict_and_busy_mutations(client):
    h = new(client); ready(client, h)
    FakeBuddy.wait = threading.Event()
    assert ask(client, h).status_code == 202
    assert ask(client, h).status_code == 202
    progress = client.get('/api/job', headers=h).json()
    assert set(progress) == {'job'} and progress['job']['state'] == 'running'
    assert ask(client, h, 'b' * 16).status_code == 409
    assert client.post('/api/reset', headers=h).status_code == 409
    assert client.delete('/api/dataset', headers=h).status_code == 409
    conflict = client.post('/api/messages', headers=h, json={'question': 'Different?', 'request_id': 'a' * 16})
    assert conflict.status_code == 409
    FakeBuddy.wait.set()
    s = wait(client, h)
    assert FakeBuddy.count == 1 and s['usage']['used'] == 1 and s['usage']['total'] == 1000


def test_global_admission_and_expiry_do_not_interrupt_work(client):
    h, other = new(client), new(client); ready(client, h); ready(client, other)
    FakeBuddy.wait = threading.Event()
    ask(client, h)
    assert ask(client, other).status_code == 503
    s = client.app.state.sessions[h['Authorization'].split()[1]]
    s.touched = time.monotonic() - main.SESSION_TTL - 1
    assert client.get('/api/session', headers=h).status_code == 200
    FakeBuddy.wait.set(); wait(client, h)
    s.touched = time.monotonic() - main.SESSION_TTL - 1
    assert client.get('/api/session', headers=h).status_code == 401


def test_allowance_adjustment_only_once_reset_and_remove_keep_budget(client):
    h = new(client); ready(client, h); FakeBuddy.total = 20_000
    for i in range(3):
        ask(client, h, f'{i:016d}'); s = wait(client, h)
    assert s['usage']['allowance'] == 13 and s['usage']['remaining'] == 10
    cleared = client.post('/api/reset', headers=h).json()
    assert cleared['turns'] == [] and cleared['usage']['used'] == 3
    removed = client.delete('/api/dataset', headers=h).json()
    assert removed['usage']['allowance'] == 13 and removed['dataset'] is None
    ready(client, h)
    for i in range(3, 13):
        assert ask(client, h, f'{i:016d}').status_code == 202
        s = wait(client, h)
    assert s['usage']['remaining'] == 0 and s['usage']['allowance'] == 13
    assert ask(client, h, 'z' * 16).status_code == 429


def test_unknown_usage_never_fabricates_or_reduces_allowance(client, monkeypatch):
    monkeypatch.setattr(FakeBuddy, 'ask', lambda self, q: AskResult('No metadata'))
    h = new(client); ready(client, h)
    for i in range(3):
        ask(client, h, f'{i:016d}'); s = wait(client, h)
    assert not s['usage']['complete'] and s['usage']['calls'] == [] and s['usage']['allowance'] == 15


def test_errors_are_sanitized_and_count_once(client, monkeypatch):
    def fail(self, q): raise RuntimeError('PRIVATE BODY key-secret')
    monkeypatch.setattr(FakeBuddy, 'ask', fail)
    h = new(client); ready(client, h); ask(client, h)
    s = wait(client, h)
    assert 'PRIVATE' not in str(s) and s['turns'][0]['status'] == 'error'
    assert s['usage']['used'] == 1


def test_session_cap_and_frame_admission(client, monkeypatch):
    h = new(client)
    monkeypatch.setattr(main, 'MAX_FRAME_BYTES', 1)
    assert client.post('/api/sample', headers=h).status_code == 413
    assert client.get('/api/session', headers=h).json()['dataset'] is None
    for _ in range(main.MAX_SESSIONS - 1): new(client)
    assert client.post('/api/session').status_code == 503


def test_usage_allowlist_and_context_cleanup():
    events = []
    response = SimpleNamespace(usage_metadata=SimpleNamespace(prompt_token_count=9, candidates_token_count=3, total_token_count=14, thoughts_token_count=2, cached_content_token_count=1), text='PRIVATE')
    with telemetry.observe(events):
        telemetry.event('attempt', provider='Gemini')
        telemetry.record_usage(response, 'Gemini', 'model')
    telemetry.event('attempt', provider='not recorded')
    usage = telemetry.summarize(events)
    assert usage['total'] == 14 and usage['complete'] and len(events) == 2
    assert 'PRIVATE' not in str(usage)


def test_real_groq_metadata_collected_without_network(monkeypatch):
    import groq
    import httpx
    import config
    real = groq.Groq
    monkeypatch.setattr(config, 'GROQ_API_KEY', 'offline-key')
    def respond(request):
        return httpx.Response(200, headers={'x-ratelimit-remaining-requests': '29', 'x-ratelimit-reset-tokens': '12.5s', 'x-private': 'SECRET'}, json={'id': 'offline', 'object': 'chat.completion', 'created': 1, 'model': config.ANALYSIS_MODEL,
            'choices': [{'index': 0, 'message': {'role': 'assistant', 'content': 'Answer'}, 'finish_reason': 'stop'}],
            'usage': {'prompt_tokens': 20, 'completion_tokens': 8, 'total_tokens': 28}})
    def factory(**kwargs):
        return real(**kwargs, http_client=httpx.Client(transport=httpx.MockTransport(respond)))
    monkeypatch.setattr(groq, 'Groq', factory)
    events = []
    with telemetry.observe(events):
        assert llm_clients.call_analysis_llm('offline question') == 'Answer'
    assert telemetry.summarize(events)['total'] == 28
    assert telemetry.summarize(events)['limits'][0]['values']['x-ratelimit-remaining-requests'] == '29'
    assert 'SECRET' not in str(events)


def test_message_validation_and_streamed_body_limit(client):
    h = new(client); ready(client, h)
    for question in (' ', 'x' * 4001):
        assert client.post('/api/messages', headers=h, json={'question': question, 'request_id': 'v' * 16}).status_code == 422
    response = client.post('/api/messages', headers={**h, 'Content-Type': 'application/json'}, content=iter([b'x' * 10_000] * 3))
    assert response.status_code == 413
    assert client.get('/api/session', headers=h).json()['usage']['used'] == 0


def test_partial_result_survives_api_serialization(client, monkeypatch):
    monkeypatch.setattr(FakeBuddy, 'ask', lambda self, q: AskResult('Explanation unavailable', chart_json='{"data":[],"layout":{}}', result_text='1000', code='result=1000', status='partial'))
    h = new(client); ready(client, h); ask(client, h)
    turn = wait(client, h)['turns'][0]
    assert turn['status'] == 'partial' and turn['chart_json'] and turn['result_text'] == '1000'
