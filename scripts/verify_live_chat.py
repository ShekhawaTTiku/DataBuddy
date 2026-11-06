"""Opt-in synthetic chat/upload acceptance. Prints checks, never response bodies."""
import argparse
import json
import re
import time
import uuid
from pathlib import Path
from urllib.parse import urlparse

import httpx


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live', action='store_true')
    parser.add_argument('--base-url', default='http://127.0.0.1:8000')
    parser.add_argument('--write-browser-fixtures', action='store_true', help='Write synthetic CSV/XLSX inputs without provider calls.')
    args = parser.parse_args()
    if args.write_browser_fixtures:
        import pandas as pd
        destination = Path(__file__).resolve().parents[1] / 'output' / 'playwright'
        destination.mkdir(parents=True, exist_ok=True)
        pd.DataFrame({'Region': ['North', 'South', 'North', 'South'], 'Sales': [100, 200, 300, 400]}).to_csv(destination / 'hosted-upload.csv', index=False)
        pd.DataFrame({'Region': ['North', 'South', 'West'], 'Sales': [10, 20, 30]}).to_excel(destination / 'hosted-replacement.xlsx', index=False)
        print('Wrote synthetic hosted-browser CSV/XLSX fixtures; no provider calls.')
        return
    if not args.live:
        parser.error('Pass --live to authorize provider quota usage.')
    parsed = urlparse(args.base_url)
    if parsed.hostname not in {'127.0.0.1', 'localhost', 'databuddynew.onrender.com'}:
        parser.error('Use the local API or the approved Render service.')
    checks = []
    progressive_requests = 0
    with httpx.Client(base_url=args.base_url.rstrip('/') + '/api/', timeout=120) as client:
        response = client.post('session')
        response.raise_for_status()
        headers = {'Authorization': 'Bearer ' + response.json()['token']}

        def snapshot():
            response = client.get('session', headers=headers)
            response.raise_for_status()
            return response.json()

        def ask(question):
            nonlocal progressive_requests
            request_id = uuid.uuid4().hex
            response = client.post('messages', headers=headers, json={'question': question, 'request_id': request_id})
            response.raise_for_status()
            deadline = time.monotonic() + 150
            lengths = set()
            with client.stream('GET', f'jobs/{request_id}/events', headers=headers) as stream:
                stream.raise_for_status()
                for line in stream.iter_lines():
                    assert time.monotonic() < deadline, 'Stream exceeded the acceptance deadline'
                    if line.startswith('data: '):
                        event = json.loads(line[6:])
                        if event.get('answer') and not event.get('answer_done'):
                            lengths.add(len(event['answer']))
            progressive_requests += len(lengths) > 1
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
        assert turn['code'] and re.search(r'\b1,?000(?:\.0+)?\b', turn['result_text'] or ''), json.dumps({'check': 'computed total', 'status': turn['status'], 'has_code': bool(turn['code']), 'has_evidence': bool(turn['result_text'])})
        passed('actual dataset calculation')
        _, turn = ask('Create a bar chart of total Sales by Region.')
        assert turn['chart_json'] and json.loads(turn['chart_json'])['data']
        passed('actual chart generation')
        response = client.post('reset', headers=headers)
        response.raise_for_status()
        assert response.json()['dataset'] is not None and response.json()['turns'] == []
        _, turn = ask('What name should you call me?')
        assert not re.search(r'\b(?:DJ|Mira)\b', turn['answer'], re.I)
        assert re.search(r'haven.t|not (?:told|provided)|don.t know|what.*(?:name|call)|prefer', turn['answer'], re.I)
        passed('clear chat forgets the introduction')
        response = client.delete('dataset', headers=headers)
        response.raise_for_status()
        state = response.json()
        assert state['dataset'] is None and state['turns'] == [] and state['usage']['used'] == 10
        passed('remove dataset keeps usage and clears context')
        assert progressive_requests, 'No progressively delivered answer was observed'
        passed('actual incremental delivery through the configured API')
    print(json.dumps({'passed': True, 'checks': checks, 'submissions': 10, 'progressive_requests': progressive_requests}))


if __name__ == '__main__':
    main()
