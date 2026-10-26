"""Single-worker, bounded, session-only API for trusted portfolio demos.

No accounts or persisted user content. Execution is NOT a hardened sandbox.
"""
import asyncio
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from dataclasses import asdict, dataclass, field
import json
import os
import secrets
import threading
import time
from urllib.parse import unquote

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

import config
from conversation_state import ConversationState
from databuddy import DataBuddy, AskResult
from llm_clients import ProviderError
import telemetry

SESSION_TTL = 1800
MAX_SESSIONS = 4
MAX_FRAME_BYTES = 48 * 1024 * 1024
MAX_TOTAL_FRAME_BYTES = 72 * 1024 * 1024
INPUT_BASELINE = 600
# Offline prompt-envelope estimate, not a provider quota or measured account average.
EXCHANGE_BASELINE = 12_000
SAMPLE = b"Month,Region,Product,Sales,Units\n2026-01-01,North,Notebook,100,2\n2026-01-01,South,Pen,200,4\n2026-02-01,North,Pen,300,6\n2026-02-01,South,Notebook,400,8\n"


@dataclass
class Session:
    touched: float = field(default_factory=time.monotonic)
    buddy: DataBuddy | None = None
    frame_bytes: int = 0
    turns: list = field(default_factory=list)
    usage: list = field(default_factory=list)
    used: int = 0
    allowance: int = 15
    adjustment_checked: bool = False
    job: dict | None = None
    requests: dict = field(default_factory=dict)
    lock: threading.RLock = field(default_factory=threading.RLock)


class Message(BaseModel):
    question: str = Field(min_length=1, max_length=config.MAX_QUESTION_CHARS)
    request_id: str = Field(pattern=r"^[a-zA-Z0-9-]{16,64}$")


def create_app(buddy_factory=DataBuddy):
    sessions: dict[str, Session] = {}
    store_lock = threading.RLock()
    work_gate = threading.Lock()
    pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="analysis")

    def expire():
        now = time.monotonic()
        with store_lock:
            for token, session in list(sessions.items()):
                with session.lock:
                    if now - session.touched > SESSION_TTL and not is_busy(session):
                        del sessions[token]

    @asynccontextmanager
    async def lifespan(app):
        async def cleanup():
            while True:
                await asyncio.sleep(60)
                expire()
        task = asyncio.create_task(cleanup())
        yield
        task.cancel()
        pool.shutdown(wait=True, cancel_futures=True)
        sessions.clear()

    app = FastAPI(title="DataBuddy", lifespan=lifespan, docs_url=None, redoc_url=None)
    app.state.sessions = sessions
    origins = [x.strip() for x in os.getenv("DATABUDDY_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",") if x.strip()]
    if "*" in origins:
        raise ValueError("DATABUDDY_ORIGINS requires explicit frontend origins.")
    app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=False,
                       allow_methods=["GET", "POST", "PUT", "DELETE"],
                       allow_headers=["Authorization", "Content-Type", "X-Filename"])

    @app.middleware("http")
    async def protection(request: Request, call_next):
        origin = request.headers.get("origin")
        if origin and origin not in origins:
            return JSONResponse({"detail": "This frontend origin is not allowed."}, status_code=403)
        # Reject large declared bodies before FastAPI parses JSON. Uploads are streamed.
        limit = config.MAX_UPLOAD_BYTES if request.url.path == "/api/dataset" else 24_000
        try:
            declared = int(request.headers.get("content-length", "0"))
        except ValueError:
            return JSONResponse({"detail": "Invalid request size."}, status_code=400)
        if declared > limit:
            return JSONResponse({"detail": "Upload exceeds 20 MiB." if limit == config.MAX_UPLOAD_BYTES else "Request is too large."}, status_code=413)
        if request.url.path != "/api/dataset" and request.method in {"POST", "PUT"}:
            body = bytearray()
            try:
                async with asyncio.timeout(30):
                    async for chunk in request.stream():
                        body.extend(chunk)
                        if len(body) > limit:
                            return JSONResponse({"detail": "Request is too large."}, status_code=413)
                request._body = bytes(body)
            except TimeoutError:
                return JSONResponse({"detail": "Request timed out. Try again."}, status_code=408)
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        return response

    @app.exception_handler(Exception)
    async def unexpected(request, exc):
        return JSONResponse({"detail": "The server could not finish. Please try again."}, status_code=500)

    def get_session(authorization):
        expire()
        token = (authorization or "").removeprefix("Bearer ")
        with store_lock:
            s = sessions.get(token)
            if s is None:
                raise HTTPException(401, "Session expired. Start a new session and upload your data again.")
            s.touched = time.monotonic()
            return s

    def is_busy(s):
        return bool(s.job and s.job["state"] == "running")

    def idle(s):
        if is_busy(s):
            raise HTTPException(409, "Wait for the current request to finish.")

    def snapshot(s):
        with s.lock:
            dataset = None
            if s.buddy:
                d = s.buddy.dataset
                preview = d.df.head(12).copy()
                # Bound cell strings; JSON conversion normalizes dates/nulls/numeric types.
                rows = json.loads(preview.to_json(orient="values", date_format="iso"))
                rows = [[v[:240] + "…" if isinstance(v, str) and len(v) > 240 else v for v in row] for row in rows]
                numeric = [str(c) for c in d.df.select_dtypes(include="number").columns]
                categories = [str(c) for c in d.df.columns if str(c) not in numeric]
                dataset = {"filename": d.filename, "rows": len(d.df), "columns": list(map(str, d.df.columns)),
                           "preview": rows, "warnings": d.warnings, "numeric": numeric, "categories": categories}
            calls = [c for u in s.usage for c in u["calls"]]
            return {"dataset": dataset, "turns": s.turns, "job": s.job,
                    "usage": {"used": s.used, "allowance": s.allowance, "remaining": max(0, s.allowance - s.used),
                              "adjusted": s.allowance < 15, "total": sum(u["total"] for u in s.usage),
                              "complete": bool(s.usage) and all(u["complete"] for u in s.usage),
                              "calls": calls, "attempts": sum(u["attempts"] for u in s.usage),
                              "limits": [e for u in s.usage for e in u["limits"]][-10:],
                              "fallbacks": sum(u["fallbacks"] for u in s.usage),
                              "last": s.usage[-1] if s.usage else None,
                              "input_baseline": INPUT_BASELINE, "exchange_baseline": EXCHANGE_BASELINE}}

    @app.get("/api/health")
    def health():
        return {"status": "ok"}

    @app.post("/api/session", status_code=201)
    def new_session():
        expire()
        with store_lock:
            if len(sessions) >= MAX_SESSIONS:
                raise HTTPException(503, "This small demo is busy. Try again after an inactive session expires.")
            token = secrets.token_urlsafe(32)
            s = Session()
            sessions[token] = s
        return {"token": token, **snapshot(s)}

    @app.get("/api/session")
    def read_session(authorization: str | None = Header(default=None)):
        return snapshot(get_session(authorization))

    @app.get("/api/job")
    def read_job(authorization: str | None = Header(default=None)):
        s = get_session(authorization)
        with s.lock:
            return {"job": s.job}

    def load(s, payload, name):
        try:
            buddy = buddy_factory(payload, filename=name)
            size = int(buddy.dataset.df.memory_usage(deep=True).sum())
            with store_lock:
                total = sum(x.frame_bytes for x in sessions.values() if x is not s)
            if size > MAX_FRAME_BYTES or size + total > MAX_TOTAL_FRAME_BYTES:
                raise HTTPException(413, "This dataset needs more memory than the demo allows. Use fewer rows or columns.")
            with s.lock:
                s.buddy, s.frame_bytes, s.turns, s.job = buddy, size, [], None
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from None
        finally:
            with s.lock:
                if is_busy(s):
                    s.job = None
                s.touched = time.monotonic()

    async def load_request(s, request=None, sample=False):
        if not work_gate.acquire(blocking=False):
            raise HTTPException(503, "Another analysis is running. Try again shortly.")
        try:
            with s.lock:
                idle(s)
                s.job = {"state": "running", "stage": "Reading dataset"}
            if sample:
                payload, name = SAMPLE, "Sample sales.csv"
            else:
                name = unquote(request.headers.get("x-filename", ""))
                if not name or len(name) > 240 or not name.lower().endswith((".csv", ".xlsx")):
                    raise HTTPException(422, "Choose a CSV or XLSX file.")
                chunks = bytearray()
                try:
                    async with asyncio.timeout(60):
                        async for chunk in request.stream():
                            if len(chunks) + len(chunk) > config.MAX_UPLOAD_BYTES:
                                raise HTTPException(413, "Upload exceeds 20 MiB.")
                            chunks.extend(chunk)
                except TimeoutError:
                    raise HTTPException(408, "Upload timed out. Try again on a stable connection.") from None
                payload = bytes(chunks)
            await run_in_threadpool(load, s, payload, name)
            return snapshot(s)
        finally:
            with s.lock:
                if is_busy(s):
                    s.job = None
            work_gate.release()

    @app.put("/api/dataset")
    async def upload(request: Request, authorization: str | None = Header(default=None)):
        return await load_request(get_session(authorization), request=request)

    @app.post("/api/sample")
    async def sample(authorization: str | None = Header(default=None)):
        return await load_request(get_session(authorization), sample=True)

    @app.delete("/api/dataset")
    def remove(authorization: str | None = Header(default=None)):
        s = get_session(authorization)
        with s.lock:
            idle(s)
            s.buddy, s.frame_bytes, s.turns, s.job = None, 0, [], None
        return snapshot(s)

    @app.post("/api/reset")
    def reset(authorization: str | None = Header(default=None)):
        s = get_session(authorization)
        with s.lock:
            idle(s)
            if s.buddy:
                s.buddy.conversation = ConversationState()
            s.turns, s.job = [], None
        return snapshot(s)

    def complete(s, question, request_id):
        events = []
        def progress(value):
            with s.lock:
                s.job = {"id": request_id, "state": "running", "stage": value, "question": question}
        try:
            with telemetry.observe(events, progress):
                result = s.buddy.ask(question)
        except ProviderError as exc:
            result = AskResult(str(exc), status="error")
        except Exception:
            result = AskResult("The analysis could not finish. Try a simpler question.", status="error")
        finally:
            usage = telemetry.summarize(events)
            with s.lock:
                s.usage.append(usage)
                # A single review after three submissions; incomplete observations never penalize.
                if s.used >= 3 and not s.adjustment_checked:
                    s.adjustment_checked = True
                    if all(u["complete"] for u in s.usage[:3]):
                        average = sum(u["total"] for u in s.usage[:3]) / 3
                        s.allowance -= 2 if average > EXCHANGE_BASELINE * 1.5 else 1 if average > EXCHANGE_BASELINE else 0
                s.turns.append({"id": request_id, "question": question, **asdict(result)})
                s.job = {"id": request_id, "state": "done", "stage": "Ready"}
                s.touched = time.monotonic()
            work_gate.release()

    @app.post("/api/messages", status_code=202)
    def ask(message: Message, authorization: str | None = Header(default=None)):
        s = get_session(authorization)
        question = message.question.strip()
        if not question:
            raise HTTPException(422, "Enter a question first.")
        with s.lock:
            if message.request_id in s.requests:
                if s.requests[message.request_id] != question:
                    raise HTTPException(409, "This request identifier was already used for a different question.")
                return {"id": message.request_id}
            idle(s)
            if not s.buddy:
                raise HTTPException(409, "Upload data or try the sample first.")
            if s.used >= s.allowance:
                raise HTTPException(429, "This session has reached its message allowance.")
            if not work_gate.acquire(blocking=False):
                raise HTTPException(503, "Another analysis is running. Try again shortly.")
            s.used += 1
            s.requests[message.request_id] = question
            s.job = {"id": message.request_id, "state": "running", "stage": "Understanding question", "question": question}
            pool.submit(complete, s, question, message.request_id)
        return {"id": message.request_id}

    return app


app = create_app()
