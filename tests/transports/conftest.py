"""전송 시험 공용 픽스처: ASGI 앱을 백그라운드 스레드의 uvicorn 으로 띄운다."""
from __future__ import annotations

import socket
import threading
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager

import pytest
import uvicorn
from starlette.types import ASGIApp


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@contextmanager
def _serve(app: ASGIApp) -> Iterator[str]:
    port   = _free_port()
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning", loop="asyncio")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.monotonic() + 15
    while not server.started:
        if time.monotonic() > deadline or not thread.is_alive():
            raise TimeoutError("uvicorn did not start")
        time.sleep(0.05)
    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        server.should_exit = True
        thread.join(timeout=10)


@pytest.fixture
def serve_app() -> Callable[[ASGIApp], object]:
    """``with serve_app(app) as base_url`` 형태로 쓴다."""
    return _serve
