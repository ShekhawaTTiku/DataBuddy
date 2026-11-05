"""Offline prompt-size calibration. Outputs aggregate counts, never prompts.

Uses the real prompt builders and worker with synthetic model responses.
Estimates are characters/4, not model tokenization or actual provider usage.
"""
import json
import math
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.core import analyst
from backend.core import config
from backend.core import conversation_state
from backend.core import message_handler
from backend.core.databuddy import DataBuddy
from backend.api.main import SAMPLE


def main():
    config.GROQ_API_KEY = config.MISTRAL_API_KEY = config.GEMINI_API_KEY = None
    config.ENABLE_VISUALIZATION_SUGGESTIONS = False
    calls = []
    def fake(role, answer, cap):
        def respond(prompt):
            calls.append({'role': role, 'estimated_input': math.ceil(len(prompt)/4),
                          'estimated_output': math.ceil(len(answer)/4), 'output_cap': cap})
            return answer
        return respond
    message_handler.classify_message = fake('routing', '{"route":"analysis"}', config.MAX_RESPONSE_TOKENS)
    analyst.call_analysis_llm = fake('code', "result = df['Sales'].sum()", config.MAX_RESPONSE_TOKENS)
    analyst.call_narration_llm = fake('narration', 'Total sales are 1000.', config.MAX_RESPONSE_TOKENS)
    conversation_state.call_memory_llm = fake('memory', 'Discussed total sales.', config.MAX_MEMORY_RESPONSE_TOKENS)
    results = []
    for case in ('sample', 'long-context'):
        buddy = DataBuddy(SAMPLE, filename='synthetic.csv')
        if case == 'long-context':
            for i in range(6):
                buddy.conversation.add_turn('Synthetic prior question', 'Synthetic history. ' * 180, is_analysis=True)
        for i in range(3):
            calls.clear()
            buddy.ask('What are total sales?')
            results.append({'case': case, 'exchange': i+1, 'calls': len(calls),
                            'estimated_total': sum(c['estimated_input'] + c['estimated_output'] for c in calls),
                            'input_plus_output_caps': sum(c['estimated_input'] + c['output_cap'] for c in calls)})
    print(json.dumps(results))


if __name__ == '__main__': main()
