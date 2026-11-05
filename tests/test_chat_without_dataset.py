"""Model-backed chat and dataset transitions, with all providers replaced offline."""
import time
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

import analyst
import conversation_state
import message_handler
import response_stream
import telemetry
from api.main import create_app
from databuddy import DataBuddy
from llm_clients import ProviderUnavailableError


@pytest.fixture
def chat(monkeypatch):
    prompts, notes = [], []

    def provider(prompt):
        prompts.append(prompt)
        telemetry.event('attempt', provider='Fixture')
        telemetry.record_usage(SimpleNamespace(usage=SimpleNamespace(prompt_tokens=80, completion_tokens=20, total_tokens=100)), 'Fixture', 'chat')
        if 'CURRENT MESSAGE:\nprovider failure' in prompt:
            raise ProviderUnavailableError('The provider is unavailable. Try again later.')
        response_stream.text('Hello ')
        response_stream.text('from the model.')
        return 'Hello from the model.'

    def memory(prompt):
        notes.append(prompt)
        return 'The user introduced themselves as Mira.'

    def unexpected(*args, **kwargs):
        raise AssertionError('Dataset-free chat must not classify or generate calculations')

    monkeypatch.setattr(message_handler, 'call_conversation_llm', provider)
    monkeypatch.setattr(message_handler, 'classify_message', unexpected)
    monkeypatch.setattr(analyst, 'generate_code', unexpected)
    monkeypatch.setattr(analyst, 'generate_chart_code', unexpected)
    monkeypatch.setattr(conversation_state, 'call_memory_llm', memory)
    with TestClient(create_app()) as client:
        headers = {'Authorization': 'Bearer ' + client.post('/api/session').json()['token']}
        yield client, headers, prompts, notes


def send(client, headers, question, number=1):
    key = f'{number:016d}'
    payload = {'question': question, 'request_id': key}
    response = client.post('/api/messages', headers=headers, json=payload)
    assert response.status_code == 202, response.text
    for _ in range(400):
        state = client.get('/api/session', headers=headers).json()
        if state['job']['state'] == 'done':
            return state
        time.sleep(.01)
    raise AssertionError('Chat did not finish')


@pytest.mark.parametrize('question', [
    '  Hi, my name is Mira!  ', 'hello!!!', 'Namaste', 'Call me DJ instead',
    "I'm having trouble uploading", 'What is a mean?', 'Hi, calculate sales',
    'Explain the previous chart', "What's my name?", 'Thank you',
])
def test_messages_before_upload_use_the_model_and_no_calculations(chat, question):
    client, headers, prompts, notes = chat
    state = send(client, headers, question)
    assert state['dataset'] is None and state['usage']['used'] == 1
    turn = state['turns'][0]
    assert turn['question'] == question.strip() and turn['answer'] == 'Hello from the model.'
    assert turn['code'] is None and turn['chart_json'] is None and turn['result_text'] is None
    assert len(prompts) == len(notes) == 1
    assert 'No dataset is loaded' in prompts[0] and 'Never invent rows' in prompts[0]
    assert question.strip() in prompts[0]
    assert 'Current server clock' in prompts[0]


def test_first_upload_preserves_chat_and_memory_but_replacement_resets(chat):
    client, headers, prompts, notes = chat
    for i in range(1, 7):
        before = send(client, headers, 'Hi, my name is Mira' if i == 1 else 'Thanks', i)
    session = client.app.state.sessions[headers['Authorization'].split()[1]]
    memory = session.buddy.conversation
    assert len(notes) == 6 and memory.memory_summary and not memory.memory_notes
    assert client.put('/api/dataset', headers={**headers, 'X-Filename': 'bad.csv'}, content=b'a,b\n1\n').status_code == 422
    assert session.buddy.conversation is memory
    assert client.get('/api/session', headers=headers).json()['turns'] == before['turns']
    uploaded = client.post('/api/sample', headers=headers).json()
    assert uploaded['dataset']['rows'] == 4 and uploaded['turns'] == before['turns']
    assert uploaded['usage']['used'] == 6 and session.buddy.conversation is memory
    replaced = client.post('/api/sample', headers=headers).json()
    assert replaced['turns'] == [] and replaced['usage']['used'] == 6
    assert session.buddy.conversation is not memory
    assert not session.buddy.conversation.memory_summary


def test_dataset_free_reset_removal_isolation_and_duplicate_requests(chat):
    client, headers, prompts, notes = chat
    state = send(client, headers, 'Hi, my name is Mira')
    assert send(client, headers, 'Hi, my name is Mira')['turns'] == state['turns']
    assert len(prompts) == 1
    other = {'Authorization': 'Bearer ' + client.post('/api/session').json()['token']}
    assert client.get('/api/session', headers=other).json()['turns'] == []
    reset = client.post('/api/reset', headers=headers).json()
    assert reset['dataset'] is None and reset['turns'] == [] and reset['usage']['used'] == 1
    send(client, headers, "What's my name?", 2)
    assert 'Mira' not in prompts[-1]
    removed = client.delete('/api/dataset', headers=headers).json()
    assert removed['turns'] == [] and removed['usage']['used'] == 2
    send(client, headers, 'Hi again', 3)
    assert 'Mira' not in prompts[-1]


def test_dataset_free_provider_failure_and_allowance(chat):
    client, headers, prompts, notes = chat
    state = send(client, headers, 'provider failure')
    assert state['turns'][0]['status'] == 'error' and state['dataset'] is None
    for i in range(2, 16):
        state = send(client, headers, 'Hello', i)
    assert state['usage']['used'] == 15 and state['usage']['remaining'] == 0
    assert client.post('/api/messages', headers=headers, json={'question': 'Hi', 'request_id': 'z' * 16}).status_code == 429
    assert client.post('/api/reset', headers=headers).json()['usage']['remaining'] == 0


def test_followup_context_and_invalid_input(chat):
    client, headers, prompts, notes = chat
    send(client, headers, 'Hi, my name is Mira')
    send(client, headers, "What's my name?", 2)
    assert 'User: Hi, my name is Mira' in prompts[-1]
    for question in [' ', 'x' * 4001]:
        assert client.post('/api/messages', headers=headers, json={'question': question, 'request_id': 'x' * 16}).status_code == 422
    assert len(prompts) == 2
