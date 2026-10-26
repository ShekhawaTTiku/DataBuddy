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
import analyst
import config
import conversation_state
import message_handler
import telemetry
from llm_clients import ProviderUnavailableError

config.GROQ_API_KEY = config.GEMINI_API_KEY = config.MISTRAL_API_KEY = None
os.environ['DATABUDDY_ORIGINS'] = 'http://localhost:5173,http://127.0.0.1:5173,http://127.0.0.1:4173'
config.EXEC_TIMEOUT_SECONDS = 20
import executor
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
    return {'route': 'visualization' if 'chart' in question.lower() else 'analysis'}

def code(*args, **kwargs):
    usage(); return "result = df['Sales'].sum()"

def chart(*args, **kwargs):
    usage()
    return "result = df.groupby('Region')['Sales'].sum().reset_index()\nfig = px.bar(result, x='Region', y='Sales', color_discrete_sequence=['#26736B'])\nchart_description = 'Sales by region'"

def answer(profile, question, code, execution, **kwargs):
    usage()
    if 'partial' in question.lower(): raise ProviderUnavailableError('Explanation unavailable.')
    return 'Total sales are **' + execution.result_text + '**.\n\nOpen Result data to inspect the calculation.'

def insight(profile, question, code, execution):
    usage()
    if 'partial' in question.lower(): raise ProviderUnavailableError('Explanation unavailable.')
    return '**South** has sales of **600**, compared with **400** in North.'

message_handler.route_message = route
analyst.generate_code = code
analyst.generate_chart_code = chart
analyst.write_answer = answer
analyst.write_chart_insight = insight
conversation_state.call_memory_llm = lambda prompt: 'Synthetic verification memory.'

if __name__ == '__main__':
    import uvicorn
    uvicorn.run('api.main:app', host='127.0.0.1', port=8000, access_log=False)
