"""Opt-in synthetic chat/upload acceptance. Prints checks, never response bodies."""
import argparse
import json
import re
import time
import uuid
from urllib.parse import urlparse

import httpx


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live', action='store_true')
    parser.add_argument('--base-url', default='http://127.0.0.1:8000')
    args = parser.parse_args()
    if not args.live:
        parser.error('Pass --live to authorize provider quota usage.')
    parsed = urlparse(args.base_url)
    if parsed.hostname not in {'127.0.0.1', 'localhost', 'databuddynew.onrender.com'}:
        parser.error('Use the local API or the approved Render service.')
    checks = []
    with httpx.Client(base_url=args.base_url.rstrip('/') + '/api/', timeout=120) as client:
        response = client.post('session')
        response.raise_for_status()
        headers = {'Authorization': 'Bearer ' + response.json()['token']}

        def snapshot():
            response = client.get('session', headers=headers)
            response.raise_for_status()
            return response.json()

        def ask(question):
            request_id = uuid.uuid4().hex
            response = client.post('messages', headers=headers, json={'question': question, 'request_id': request_id})
            response.raise_for_status()
            deadline = time.monotonic() + 150
            while time.monotonic() < deadline:
                state = snapshot()
                if state['job']['state'] == 'done':
                    turn = state['turns'][-1]
                    assert turn['status'] in {'success', 'partial'}, 'Model request did not complete successfully'
                    return state, turn
                time.sleep(.5)
            raise AssertionError('Model request exceeded the acceptance deadline')

        def passed(label):
            checks.append(label)
            print(json.dumps({'check': label, 'passed': True}), flush=True)

        state, turn = ask('Hi, my name is Mira. Please keep your replies brief.')
        assert state['dataset'] is None and 'mira' in turn['answer'].lower()
        passed('model greeting before upload')
        ask('Actually, call me DJ instead.')
        _, turn = ask('What name should you call me now?')
        assert re.search(r'\bDJ\b', turn['answer'], re.I)
        passed('name correction and recall')
        ask("I'm having trouble uploading. Which file types can I use?")
        _, turn = ask('Hi, calculate my total sales and create a chart.')
        assert re.search(r'upload|sample|dataset|file', turn['answer'], re.I)
        assert turn['code'] is None and turn['chart_json'] is None
        passed('mixed request invites data without executing calculations')
        state, _ = ask('Describe three things you can help me do.')
        before = len(state['turns'])
        response = client.post('sample', headers=headers)
        response.raise_for_status()
        state = response.json()
        assert len(state['turns']) == before and state['dataset']['rows'] == 4
        _, turn = ask('What name should you call me?')
        assert re.search(r'\bDJ\b', turn['answer'], re.I)
        passed('first upload preserves chat and memory across six exchanges')
        _, turn = ask('What is the total Sales across all rows?')
        assert turn['code'] and '1000' in turn['result_text']
        passed('actual dataset calculation')
        _, turn = ask('Create a bar chart of total Sales by Region.')
        assert turn['chart_json'] and json.loads(turn['chart_json'])['data']
        passed('actual chart generation')
        response = client.post('reset', headers=headers)
        response.raise_for_status()
        assert response.json()['dataset'] is not None and response.json()['turns'] == []
        _, turn = ask('What name should you call me?')
        assert not re.search(r'\b(?:DJ|Mira)\b', turn['answer'], re.I)
        passed('clear chat forgets the introduction')
        response = client.delete('dataset', headers=headers)
        response.raise_for_status()
        state = response.json()
        assert state['dataset'] is None and state['turns'] == [] and state['usage']['used'] == 10
        passed('remove dataset keeps usage and clears context')
    print(json.dumps({'passed': True, 'checks': checks, 'submissions': 10}))


if __name__ == '__main__':
    main()
