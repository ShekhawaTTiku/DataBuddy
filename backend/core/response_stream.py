"""Request-local response delivery; no persistence and no provider bodies in logs."""
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
import threading

from backend.core import config
class ResponseCancelled(Exception):
    """The user stopped this exchange; bookkeeping still finishes once."""


class Cancellation(threading.Event):
    """Signal the worker and best-effort close a provider stream blocked on IO."""
    def __init__(self):
        super().__init__()
        self._closer = None
        self._lock = threading.Lock()

    def bind(self, closer):
        with self._lock:
            self._closer = closer
        if self.is_set() and closer:
            self.set()

    def set(self):
        super().set()
        with self._lock:
            closer = self._closer
        if closer:
            try:
                closer()
            except Exception:
                pass


@dataclass
class Delivery:
    callback: object
    cancelled: threading.Event
    answer: str = ""
    evidence: dict = field(default_factory=dict)
    finalizing: bool = False


_current = ContextVar("databuddy_response_delivery", default=None)


@contextmanager
def observe(callback, cancelled):
    delivery = Delivery(callback, cancelled)
    token = _current.set(delivery)
    try:
        yield delivery
    finally:
        _current.reset(token)


def current():
    return _current.get()


def check_cancelled():
    delivery = current()
    if delivery and not delivery.finalizing and delivery.cancelled.is_set():
        raise ResponseCancelled()


@contextmanager
def connection(client):
    delivery = current()
    bind = getattr(delivery.cancelled, "bind", None) if delivery and not delivery.finalizing else None
    if bind:
        close = getattr(client, "close", None) or (lambda: client.__exit__(None, None, None))
        bind(close)
    try:
        check_cancelled()
        yield
    finally:
        if bind:
            bind(None)


def emit(kind, **values):
    delivery = current()
    if delivery:
        delivery.callback(kind, values)


def text(value):
    check_cancelled()
    delivery = current()
    if delivery and value:
        remaining = config.MAX_MESSAGE_CHARS - len(delivery.answer)
        delivery.answer += value[:max(0, remaining)]
        emit("text", answer=delivery.answer)


def reset_answer(notice=""):
    check_cancelled()
    delivery = current()
    if delivery:
        delivery.answer = ""
        emit("reset", notice=notice)


def evidence(**values):
    delivery = current()
    if delivery:
        delivery.evidence = values
        emit("evidence", **values)
    # A completed computation survives cancellation at the handoff to narration.
    check_cancelled()


def finish(result):
    delivery = current()
    if delivery:
        delivery.finalizing = True
        delivery.answer = result.answer
        emit("answer_done", answer=result.answer, status=result.status)
