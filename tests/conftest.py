"""Regression tests are offline and never use the owner's provider credentials."""
import socket

import pytest

from backend.core import config
@pytest.fixture(autouse=True)
def offline_only(monkeypatch):
    original_connect = socket.socket.connect
    def reject_network(sock, address, *args, **kwargs):
        # Windows asyncio uses a local socket pair for its internal event loop.
        if isinstance(address, tuple) and address[0] in {"127.0.0.1", "::1"}:
            return original_connect(sock, address, *args, **kwargs)
        raise AssertionError("Regression tests must not make network requests.")
    monkeypatch.setattr(socket.socket, "connect", reject_network)
    monkeypatch.setattr(config, "GROQ_API_KEY", None)
    monkeypatch.setattr(config, "MISTRAL_API_KEY", None)
    monkeypatch.setattr(config, "GEMINI_API_KEY", None)
