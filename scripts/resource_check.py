"""Offline synthetic resource probe; prints only size/timing/peak RSS metadata.

Run on the actual Linux host/image too: Windows results do not certify Render.
"""
import argparse
import io
import json
from pathlib import Path
import sys
import threading
import time
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import psutil


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--case', choices=['sample', 'near-limit', 'wide', 'xlsx'], default='sample')
    args = parser.parse_args()
    proc = psutil.Process()
    peak = [0]
    done = threading.Event()
    def measure():
        while not done.wait(.02):
            processes = [proc] + proc.children(recursive=True)
            total = 0
            for p in processes:
                try: total += p.memory_info().rss
                except psutil.Error: pass
            peak[0] = max(peak[0], total)
    monitor = threading.Thread(target=measure, daemon=True); monitor.start()
    started = time.monotonic()
    from backend.core import config
    from backend.core import executor
    from backend.core.databuddy import DataBuddy
    # Include providers/API loaded in a warm process, without making requests.
    import groq
    import google.genai
    import mistralai.client
    import backend.api.main
    executor.EXEC_TIMEOUT_SECONDS = 30
    if args.case == 'sample':
        from backend.api.main import SAMPLE
        payload = SAMPLE
    elif args.case == 'near-limit':
        # 240k rows, ~19.5 MiB, low-cardinality strings. All synthetic.
        payload = b'Region,Sales,Note\n' + (b'North,12,' + b'x' * 75 + b'\n') * 240_000
    elif args.case == 'wide':
        payload = (','.join(f'c{i}' for i in range(200)) + '\n').encode() + (','.join('123456789' for _ in range(200)) + '\n').encode() * 10_000
    else:
        import pandas as pd
        buffer = io.BytesIO()
        pd.DataFrame({'Region': ['North', 'South'] * 10000, 'Sales': list(range(20000))}).to_excel(buffer, index=False)
        payload = buffer.getvalue()
    buddy = DataBuddy(payload, filename='synthetic.xlsx' if args.case == 'xlsx' else 'synthetic.csv')
    loaded = time.monotonic()
    code = "result = df.select_dtypes(include='number').sum()\nfig = px.bar(x=['A','B'], y=[1,2])"
    result = executor.run_code(code, buddy.dataset.df)
    done.set(); monitor.join()
    print(json.dumps({'platform': sys.platform, 'case': args.case, 'upload_mib': round(len(payload)/2**20, 2),
                      'frame_mib': round(int(buddy.dataset.df.memory_usage(deep=True).sum())/2**20, 2),
                      'peak_parent_worker_mib': round(peak[0]/2**20, 2),
                      'load_seconds': round(loaded-started, 2), 'worker_seconds': round(time.monotonic()-loaded, 2),
                      'execution_ok': result.ok}))


if __name__ == '__main__': main()
