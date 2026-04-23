"""Integration test: stdio + http simultaneous startup."""
from __future__ import annotations

import subprocess
import sys
import time
import urllib.request

_PORT = 19997
_TOKEN = "multi-test-token"  # noqa: S105
_TIMEOUT = 20


def _wait_for_http(port: int, timeout: float = _TIMEOUT) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/healthz", timeout=2):  # noqa: S310
                return
        except Exception:
            time.sleep(0.25)
    raise TimeoutError(f"HTTP transport not ready within {timeout}s")


def test_stdio_http_simultaneous_startup() -> None:
    cmd = [
        sys.executable, "-m", "sootool",
        "--transport", "stdio,http",
        "--http-port", str(_PORT),
        "--auth-token", _TOKEN,
        "--log-format", "text",
        "--log-level", "WARNING",
    ]
    proc = subprocess.Popen(  # noqa: S603
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        _wait_for_http(_PORT)

        with urllib.request.urlopen(f"http://127.0.0.1:{_PORT}/healthz", timeout=5) as r:  # noqa: S310
            import json
            data = json.loads(r.read())
        assert data["status"] == "ok"
        assert data["tools"] > 20
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


def test_http_only_binds_and_responds() -> None:
    port = _PORT + 1
    cmd = [
        sys.executable, "-m", "sootool",
        "--transport", "http",
        "--http-port", str(port),
        "--auth-token", _TOKEN,
        "--log-format", "text",
    ]
    proc = subprocess.Popen(cmd, stderr=subprocess.PIPE)  # noqa: S603
    try:
        _wait_for_http(port)

        req = urllib.request.Request(
            f"http://127.0.0.1:{port}/healthz",
        )
        with urllib.request.urlopen(req, timeout=5) as r:  # noqa: S310
            import json
            data = json.loads(r.read())
        assert data["status"] == "ok"
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


def test_host_0000_without_token_exits_nonzero() -> None:
    cmd = [
        sys.executable, "-m", "sootool",
        "--transport", "http",
        "--host", "0.0.0.0",  # noqa: S104
    ]
    result = subprocess.run(cmd, capture_output=True, timeout=10)  # noqa: S603
    assert result.returncode != 0
    stderr = result.stderr.decode()
    assert "auth" in stderr.lower() or "token" in stderr.lower()
