"""Tests for scripts/capture_development_head.py."""
from __future__ import annotations

import base64
import hashlib
import importlib.util
import json
import os
import signal
import sys
import threading
from pathlib import Path
from types import SimpleNamespace

import pytest

REPO = Path("/private/tmp/p22-input-feasibility.WhUFn3/workspace")
SCRIPTS = REPO / "scripts"
PINNED_URL = (
    "https://ftp.ncbi.nlm.nih.gov/geo/series/GSE305nnn/GSE305146/suppl/"
    "GSE305146_seur_integr_labelled_exc_lin_PCW10_20.rda.gz"
)
PINNED_TS = "2024-01-01T00:00:00Z"
DEADLINE = 15.0


def _load_capture(monkeypatch):
    monkeypatch.syspath_prepend(str(SCRIPTS))
    spec = importlib.util.spec_from_file_location(
        "capture_development_head", SCRIPTS / "capture_development_head.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _make_fake_signal():
    state = {"handlers": {}, "timers": {}}
    for sig in (signal.SIGALRM, signal.SIGINT, signal.SIGTERM):
        state["handlers"][sig] = signal.default_int_handler if sig == signal.SIGINT else None
    state["timers"][signal.ITIMER_REAL] = (0.0, 0.0)
    state["timers"][signal.ITIMER_PROF] = (0.0, 0.0)
    state["timers"][signal.ITIMER_VIRTUAL] = (0.0, 0.0)

    def getsignal(sig):
        return state["handlers"].get(sig)

    def signal_set(sig, handler):
        prev = state["handlers"].get(sig)
        state["handlers"][sig] = handler
        return prev

    def getitimer(which):
        return state["timers"].get(which, (0.0, 0.0))

    def setitimer(which, seconds, interval=0.0):
        prev = state["timers"].get(which, (0.0, 0.0))
        state["timers"][which] = (seconds, interval)
        return prev

    ns = SimpleNamespace(
        SIGALRM=signal.SIGALRM,
        ITIMER_REAL=signal.ITIMER_REAL,
        getsignal=getsignal,
        signal=signal_set,
        getitimer=getitimer,
        setitimer=setitimer,
    )
    return ns, state


def _make_clock(start=0.0, step=0.0):
    state = {"now": start, "step": step}

    def tick():
        state["now"] += state["step"]
        return state["now"]

    return tick, state


class TransportHarness:
    def __init__(self, recv_chunks, request_side_effect=None, close_side_effect=None):
        self.recv_chunks = list(recv_chunks)
        self.request_side_effect = request_side_effect
        self.close_side_effect = close_side_effect
        self.requests = []
        self.closed = False
        self.sock = SimpleNamespace(
            recv=self._recv,
            settimeout=lambda t: None,
            timeout=None,
        )
        self.timeout = None

    def _recv(self, n):
        if not self.recv_chunks:
            return b""
        chunk = self.recv_chunks.pop(0)
        return chunk[:n]

    def request(self, method, path, body=None, headers=None):
        self.requests.append((method, path, body, headers))
        if self.request_side_effect:
            self.request_side_effect()

    def close(self):
        if self.close_side_effect:
            self.close_side_effect()
        self.closed = True

    def factory(self, host, port=443, timeout=None):
        self.timeout = timeout
        return self


@pytest.fixture(autouse=True)
def deny_live_network(monkeypatch):
    import socket

    def _deny(*a, **k):
        raise AssertionError("live network access attempted")

    monkeypatch.setattr(socket, "create_connection", _deny)
    monkeypatch.setattr(socket, "getaddrinfo", _deny)
    monkeypatch.setattr(socket.socket, "connect", _deny)
    monkeypatch.setattr(socket.socket, "connect_ex", _deny)


@pytest.fixture
def cap_env(monkeypatch):
    mod = _load_capture(monkeypatch)
    fake_sig, sig_state = _make_fake_signal()
    monkeypatch.setattr(mod, "_signal", fake_sig)
    clock, clock_state = _make_clock()
    monkeypatch.setattr(mod, "_monotonic", clock)
    monkeypatch.setattr(mod, "threading", threading)
    return SimpleNamespace(mod=mod, sig_state=sig_state, clock_state=clock_state)


def _valid_headers():
    return (
        b"HTTP/1.1 200 OK\r\n"
        b"Content-Length: 12345\r\n"
        b"ETag: \"abc\"\r\n"
        b"Last-Modified: Wed, 21 Oct 2015 07:28:00 GMT\r\n"
        b"Accept-Ranges: bytes\r\n"
        b"\r\n"
    )


def _valid_chunks():
    hdr = _valid_headers()
    return [hdr[:32], hdr[32:]]


def _expected_report(url, ts, raw, req_count=1):
    sha = hashlib.sha256(raw).hexdigest() if raw else None
    return {
        "capture_status": "CAPTURED",
        "reason": None,
        "url": url,
        "observed_at": ts,
        "requests_attempted": req_count,
        "header_bytes": len(raw),
        "raw_header_base64": base64.b64encode(raw).decode("ascii"),
        "header_record_sha256": sha,
        "metadata": None,
        "body_bytes": 0,
        "scientific_gate_effect": "NONE",
    }


def _refused_report(url, ts, reason, raw=b"", req_count=0):
    sha = hashlib.sha256(raw).hexdigest() if raw else None
    return {
        "capture_status": "REFUSED",
        "reason": reason,
        "url": url if url else None,
        "observed_at": ts if ts else None,
        "requests_attempted": req_count,
        "header_bytes": len(raw),
        "raw_header_base64": base64.b64encode(raw).decode("ascii"),
        "header_record_sha256": sha,
        "metadata": None,
        "body_bytes": 0,
        "scientific_gate_effect": "NONE",
    }


def test_valid_capture(cap_env):
    from validate_development_head import parse_head_evidence

    raw = _valid_headers()
    harness = TransportHarness(_valid_chunks())
    result = cap_env.mod.capture_head(
        url=PINNED_URL,
        observed_at=PINNED_TS,
        connection_factory=harness.factory,
    )
    assert result["capture_status"] == "CAPTURED"
    assert result["requests_attempted"] == 1
    assert result["header_bytes"] == len(raw)
    assert result["raw_header_base64"] == base64.b64encode(raw).decode("ascii")
    assert result["header_record_sha256"] == hashlib.sha256(raw).hexdigest()
    assert result["body_bytes"] == 0
    assert result["scientific_gate_effect"] == "NONE"
    expected_meta = parse_head_evidence(raw, url=PINNED_URL, observed_at=PINNED_TS)
    assert result["metadata"] == expected_meta
    assert harness.requests[0][0] == "HEAD"
    assert harness.requests[0][1] == "/geo/series/GSE305nnn/GSE305146/suppl/GSE305146_seur_integr_labelled_exc_lin_PCW10_20.rda.gz"
    assert harness.requests[0][2] is None
    assert harness.requests[0][3] == {"Accept-Encoding": "identity", "Connection": "close"}
    assert harness.closed is True
    assert cap_env.sig_state["timers"][signal.ITIMER_REAL] == (0.0, 0.0)
    assert cap_env.sig_state["handlers"][signal.SIGALRM] is None


@pytest.mark.parametrize(
    "url,ts,reason",
    [
        ("http://bad.example", PINNED_TS, "BAD_TARGET"),
        (PINNED_URL, "", "BAD_LABEL"),
        (PINNED_URL, "bad\x00ts", "BAD_LABEL"),
    ],
)
def test_preflight_refusals(cap_env, url, ts, reason):
    harness = TransportHarness([])
    result = cap_env.mod.capture_head(url=url, observed_at=ts, connection_factory=harness.factory)
    assert result["capture_status"] == "REFUSED"
    assert result["reason"] == reason
    assert result["requests_attempted"] == 0
    assert harness.requests == []


def test_none_factory_refusal(cap_env):
    result = cap_env.mod.capture_head(url=PINNED_URL, observed_at=PINNED_TS, connection_factory=None)
    assert result["capture_status"] == "REFUSED"
    assert result["reason"] == "LIVE_TRANSPORT_NOT_ENABLED"
    assert result["requests_attempted"] == 0


def test_exact_65536_success(cap_env):
    from validate_development_head import parse_head_evidence

    base = b"HTTP/1.1 200 OK\r\nContent-Length: 1\r\n\r\n"
    pad_len = 65536 - len(base)
    raw = base + b"A" * pad_len
    assert len(raw) == 65536
    chunks = [raw[:1000], raw[1000:]]
    harness = TransportHarness(chunks)
    result = cap_env.mod.capture_head(
        url=PINNED_URL, observed_at=PINNED_TS, connection_factory=harness.factory
    )
    assert result["capture_status"] == "CAPTURED"
    assert result["header_bytes"] == 65536
    assert result["metadata"] == parse_head_evidence(raw, url=PINNED_URL, observed_at=PINNED_TS)
    assert harness.closed is True


def test_header_cap_65537(cap_env):
    base = b"HTTP/1.1 200 OK\r\nContent-Length: 1\r\n\r\n"
    pad_len = 65536 - len(base)
    raw = base + b"A" * pad_len + b"B"
    assert len(raw) == 65537
    chunks = [raw[:1000], raw[1000:]]
    harness = TransportHarness(chunks)
    result = cap_env.mod.capture_head(
        url=PINNED_URL, observed_at=PINNED_TS, connection_factory=harness.factory
    )
    assert result["capture_status"] == "REFUSED"
    assert result["reason"] == "HEADER_CAP"
    assert result["header_bytes"] == 65536
    assert harness.closed is True


def test_many_small_headers_overflow(cap_env):
    lines = [b"HTTP/1.1 200 OK\r\n"]
    total = len(lines[0])
    i = 0
    while total < 65536:
        line = f"X-Header-{i}: value\r\n".encode()
        lines.append(line)
        total += len(line)
        i += 1
    raw = b"".join(lines) + b"\r\n"
    assert len(raw) > 65536
    chunks = [raw[:1000], raw[1000:]]
    harness = TransportHarness(chunks)
    result = cap_env.mod.capture_head(
        url=PINNED_URL, observed_at=PINNED_TS, connection_factory=harness.factory
    )
    assert result["capture_status"] == "REFUSED"
    assert result["reason"] == "HEADER_CAP"
    assert result["header_bytes"] == 65536


@pytest.mark.parametrize(
    "raw,reason",
    [
        (b"HTTP/1.1 301 Moved\r\nLocation: /new\r\n\r\n", "PARSER_REFUSAL"),
        (b"HTTP/1.1 200 OK\r\nContent-Length: 1\r\nContent-Encoding: gzip\r\n\r\n", "ENCODING_REFUSAL"),
        (b"HTTP/1.1 200 OK\r\nContent-Length: 1\r\nContent-Encoding: gzip\r\nContent-Encoding: gzip\r\n\r\n", "ENCODING_REFUSAL"),
        (b"HTTP/1.1 200 OK\r\nContent-Length: 0\r\n\r\n", "PARSER_REFUSAL"),
    ],
)
def test_parser_and_encoding_refusals(cap_env, raw, reason):
    harness = TransportHarness([raw])
    result = cap_env.mod.capture_head(
        url=PINNED_URL, observed_at=PINNED_TS, connection_factory=harness.factory
    )
    assert result["capture_status"] == "REFUSED"
    assert result["reason"] == reason
    assert result["requests_attempted"] == 1
    assert result["header_bytes"] == len(raw)
    assert harness.closed is True


def test_eof_truncation(cap_env):
    raw = b"HTTP/1.1 200 OK\r\nContent-Length: 1\r\n"
    harness = TransportHarness([raw])
    result = cap_env.mod.capture_head(
        url=PINNED_URL, observed_at=PINNED_TS, connection_factory=harness.factory
    )
    assert result["capture_status"] == "REFUSED"
    assert result["reason"] == "TRUNCATION"
    assert result["header_bytes"] == len(raw)
    assert harness.closed is True


def test_io_failure(cap_env):
    class BadSock:
        def recv(self, n):
            raise OSError("io error")
        def settimeout(self, t):
            pass
        timeout = None

    harness = TransportHarness([])
    harness.sock = BadSock()
    result = cap_env.mod.capture_head(
        url=PINNED_URL, observed_at=PINNED_TS, connection_factory=harness.factory
    )
    assert result["capture_status"] == "REFUSED"
    assert result["reason"] == "IO_FAILURE"
    assert harness.closed is True


def test_deadline_expired_slow_trickle(cap_env):
    raw = _valid_headers()
    chunks = [raw[:10], raw[10:20], raw[20:]]
    harness = TransportHarness(chunks)
    cap_env.clock_state["step"] = 5.0
    result = cap_env.mod.capture_head(
        url=PINNED_URL, observed_at=PINNED_TS, connection_factory=harness.factory
    )
    assert result["capture_status"] == "REFUSED"
    assert result["reason"] == "DEADLINE_EXPIRED"
    assert harness.closed is True


def test_late_factory_returns_closes_no_request(cap_env):
    class LateFactory:
        def __call__(self, host, port=443, timeout=None):
            cap_env.clock_state["now"] = 20.0
            conn = SimpleNamespace(
                request=lambda *a, **k: None,
                sock=SimpleNamespace(recv=lambda n: b"", settimeout=lambda t: None, timeout=None),
                close=lambda: setattr(self, "closed", True),
                timeout=None,
            )
            self.closed = False
            return conn

    factory = LateFactory()
    result = cap_env.mod.capture_head(
        url=PINNED_URL, observed_at=PINNED_TS, connection_factory=factory
    )
    assert result["capture_status"] == "REFUSED"
    assert result["reason"] == "DEADLINE_EXPIRED"
    assert result["requests_attempted"] == 0
    assert factory.closed is True


def test_nonmain_thread_refusal(cap_env, monkeypatch):
    class FakeThread:
        def is_main(self):
            return False

    monkeypatch.setattr(cap_env.mod.threading, "current_thread", lambda: FakeThread())
    harness = TransportHarness([])
    result = cap_env.mod.capture_head(
        url=PINNED_URL, observed_at=PINNED_TS, connection_factory=harness.factory
    )
    assert result["capture_status"] == "REFUSED"
    assert result["reason"] == "DEADLINE_UNAVAILABLE"
    assert result["requests_attempted"] == 0


def test_active_timer_refusal(cap_env):
    cap_env.sig_state["timers"][signal.ITIMER_REAL] = (1.0, 0.0)
    harness = TransportHarness([])
    result = cap_env.mod.capture_head(
        url=PINNED_URL, observed_at=PINNED_TS, connection_factory=harness.factory
    )
    assert result["capture_status"] == "REFUSED"
    assert result["reason"] == "DEADLINE_UNAVAILABLE"
    assert result["requests_attempted"] == 0
    assert cap_env.sig_state["timers"][signal.ITIMER_REAL] == (1.0, 0.0)


def test_request_exception(cap_env):
    def boom():
        raise RuntimeError("req fail")

    harness = TransportHarness([], request_side_effect=boom)
    result = cap_env.mod.capture_head(
        url=PINNED_URL, observed_at=PINNED_TS, connection_factory=harness.factory
    )
    assert result["capture_status"] == "REFUSED"
    assert result["reason"] == "IO_FAILURE"
    assert result["requests_attempted"] == 1
    assert harness.closed is True


def test_no_live_requests_on_import(cap_env):
    assert cap_env.mod.capture_head is not None
    report = cap_env.mod.capture_head(url=PINNED_URL, observed_at=PINNED_TS, connection_factory=None)
    assert report["capture_status"] == "REFUSED"
    assert report["reason"] == "LIVE_TRANSPORT_NOT_ENABLED"
    json.dumps(report)


def test_cleanup_failure_refuses_success(cap_env):
    raw = _valid_headers()
    harness = TransportHarness(_valid_chunks(), close_side_effect=lambda: (_ for _ in ()).throw(OSError("close fail")))
    result = cap_env.mod.capture_head(
        url=PINNED_URL, observed_at=PINNED_TS, connection_factory=harness.factory
    )
    assert result["capture_status"] == "REFUSED"
    assert result["reason"] == "IO_FAILURE"
    assert result["metadata"] is None
# END OF FILE
