"""Local browser verification ONLY. Real loader/worker/API, synthetic providers.

Never included in the Docker image. No live API calls or account quota used.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import socket
import os
import time
from types import SimpleNamespace
from backend.core import analyst
from backend.core import config
from backend.core import conversation_state
from backend.core import message_handler
from backend.core import telemetry
from backend.core import response_stream
from backend.core.llm_clients import ProviderUnavailableError

config.GROQ_API_KEY = config.GEMINI_API_KEY = config.MISTRAL_API_KEY = None
os.environ['DATABUDDY_ORIGINS'] = 'http://localhost:5173,http://127.0.0.1:5173,http://127.0.0.1:4173,http://127.0.0.1:5174,http://127.0.0.1:4174'
config.EXEC_TIMEOUT_SECONDS = 20
from backend.core import executor
executor.EXEC_TIMEOUT_SECONDS = 20
original_connect = socket.socket.connect
def local_only(sock, address):
    if isinstance(address, tuple) and address[0] not in ('127.0.0.1', '::1'):
        raise RuntimeError('Browser fixture forbids external network requests')
    return original_connect(sock, address)
socket.socket.connect = local_only

def usage(provider='Groq', total=5000):
    telemetry.event('attempt', provider=provider)
    response = SimpleNamespace(usage=SimpleNamespace(prompt_tokens=total - 200, completion_tokens=200, total_tokens=total))
    telemetry.record_usage(response, provider, 'offline-browser-fixture')

def route(question, **kwargs):
    usage('Mistral'); time.sleep(.3)
    if 'provider failure' in question.lower():
        raise ProviderUnavailableError('The provider is unavailable. Try again later.')
    if any(word in question.lower() for word in ['hello', 'name', 'remember']):
        return {'route': 'conversation', 'reply': ''}
    return {'route': 'visualization' if 'chart' in question.lower() else 'analysis'}

def code(*args, **kwargs):
    usage(); return "result = df['Sales'].sum()"

def chart(*args, **kwargs):
    usage()
    if 'dashboard' in str(args).lower() or 'dashboard' in str(kwargs).lower():
        return """result = df.groupby('Region')['Sales'].sum().reset_index()
fig = make_subplots(rows=2, cols=2, subplot_titles=('Monthly Sales & Profit', 'Sales by Region', 'Discount vs Profit', 'Correlation Heatmap'))
fig.add_trace(go.Scatter(x=[1, 2, 3, 4], y=[100, 200, 150, 300], name='Sales'), row=1, col=1)
fig.add_trace(go.Scatter(x=[1, 2, 3, 4], y=[20, 40, 30, 50], name='Profit'), row=1, col=1)
fig.add_trace(go.Bar(x=result['Sales'], y=result['Region'], orientation='h', name='Regional sales'), row=1, col=2)
fig.add_trace(go.Scatter(x=[0, .1, .2, .4], y=[100, 60, 20, -10], mode='markers', name='Orders'), row=2, col=1)
fig.add_trace(go.Heatmap(z=[[1, .3, -.4], [.3, 1, .2], [-.4, .2, 1]], x=['Sales', 'Quantity', 'Profit'], y=['Sales', 'Quantity', 'Profit'], colorscale='RdBu', colorbar=dict(title='Correlation')), row=2, col=2)
fig.update_xaxes(title_text='Month', row=1, col=1)
fig.update_yaxes(title_text='Amount (USD)', row=1, col=1)
fig.update_xaxes(title_text='Sales (USD)', row=1, col=2)
fig.update_xaxes(title_text='Discount', row=2, col=1)
fig.update_yaxes(title_text='Profit (USD)', row=2, col=1)
fig.update_layout(title='Synthetic Dashboard Overview', height=600)
chart_description = 'Synthetic four-panel dashboard for offline layout verification'
"""
    return "result = df.groupby('Region')['Sales'].sum().reset_index()\nfig = px.bar(result, x='Region', y='Sales', color_discrete_sequence=['#26736B'])\nchart_description = 'Sales by region'"

def incremental(text):
    if response_stream.current():
        for start in range(0, len(text), 24):
            response_stream.text(text[start:start + 24])
            time.sleep(.08)
    return text


def answer(profile, question, code, execution, **kwargs):
    usage()
    if 'fallback' in question.lower():
        response_stream.text('An unfinished primary explanation')
        time.sleep(.8)
        response_stream.reset_answer('The explanation was interrupted. Restarting with the backup provider.')
        telemetry.event('fallback')
        usage('Mistral')
        return incremental('Backup explanation: the computed total is **' + execution.result_text + '**.')
    if 'markdown' in question.lower():
        return incremental(("## Synthetic formatting check\n\n" +
                "| Metric | Value |\n| --- | --- |\n| Total | 1000 |\n\n" +
                "```python\nresult = df['Sales'].sum()\n```\n\n" +
                "$$E = mc^2$$\n\n```mermaid\ngraph LR\nA[Upload] --> B[Analyze] --> C[Result]\n```\n\n" +
                "\n\n".join(f"### Observation {i}\nSynthetic paragraph for scroll verification. " + "Readable content. " * 12 for i in range(1, 19))))
    if 'partial' in question.lower(): raise ProviderUnavailableError('Explanation unavailable.')
    return incremental('Total sales are **' + execution.result_text + '**.\n\nOpen Result data to inspect the calculation.')

def insight(profile, question, code, execution):
    usage()
    if 'partial' in question.lower(): raise ProviderUnavailableError('Explanation unavailable.')
    time.sleep(2)  # Makes ready-chart-before-text behavior observable in browser checks.
    return incremental('**South** has sales of **600**, compared with **400** in North.')


def memory(prompt):
    time.sleep(.8)
    return 'Synthetic verification memory.'

message_handler.route_message = route
analyst.generate_code = code
analyst.generate_chart_code = chart
analyst.write_answer = answer
analyst.write_chart_insight = insight
def conversation(question, context, **kwargs):
    usage('Mistral')
    if 'provider failure' in question.lower():
        raise ProviderUnavailableError('The provider is unavailable. Try again later.')
    if 'name' in question.lower() and 'Mira' in context:
        return incremental('Your name is Mira. I remember it for this session.')
    if question.lower().startswith('hi, my name is mira'):
        return incremental('Hi Mira! How can I help you today?')
    if not kwargs.get('dataset_loaded', True) and any(word in question.lower() for word in ['sales', 'chart', 'rows']):
        return incremental('Upload your CSV or XLSX file, or choose Try sample data, so I can calculate that from your data.')
    return incremental('Hello! I can help explore your dataset, calculate results and create charts. ' * (20 if 'slow' in question.lower() else 4))

message_handler.answer_conversation = conversation
conversation_state.call_memory_llm = memory

if __name__ == '__main__':
    if '--write-ui-fixtures' in sys.argv:
        import pandas as pd
        folder = Path(__file__).resolve().parents[1] / 'output' / 'playwright'
        folder.mkdir(parents=True, exist_ok=True)
        pd.DataFrame({**{f'Metric {i}': [row+i for row in range(60)] for i in range(18)},
                      'Region': ['North', 'South'] * 30, 'Category': ['A', 'B', 'C'] * 20,
                      'Date': pd.date_range('2026-01-01', periods=60), 'Record ID': range(60)}).to_csv(folder / 'wide-suggestions.csv', index=False)
        pd.DataFrame({'Region': ['North', 'South', 'North', 'South'],
                      'Category': ['A', 'B', 'B', 'A']}).to_csv(folder / 'text-suggestions.csv', index=False)
        raise SystemExit(0)
    import uvicorn
    from backend.api.main import app

    @app.get('/api/verification-fixture')
    def verification_fixture():
        return {'offline_fixture': True}

    uvicorn.run(app, host='127.0.0.1', port=int(os.getenv('DATABUDDY_FIXTURE_PORT', '8000')), access_log=False)
