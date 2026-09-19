"""Tests for scripts/capture_development_head.py."""

from __future__ import annotations

import base64
import hashlib
import importlib.util
import json
import signal
import threading
from pathlib import Path
from types import SimpleNamespace

import pytest

REPO = Path(__file__).resolve().parents[1]
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
        state["handlers"][sig] = (
            signal.default_int_handler if sig == signal.SIGINT else signal.SIG_DFL
        )
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
        SIG_DFL=signal.SIG_DFL,
        SIG_IGN=signal.SIG_IGN,
        ITIMER_REAL=signal.ITIMER_REAL,
        getsignal=getsignal,
        signal=signal_set,
        getitimer=getitimer,
        setitimer=setitimer,
    )
    return ns, state


def _make_clock(start=0.0):
    state = {"now": start}

    def tick():
        return state["now"]

    return tick, state


class TransportHarness:
    def __init__(
        self,
        recv_chunks,
        *,
        clock_state,
        request_side_effect=None,
        close_side_effect=None,
        recv_cost=0,
        factory_cost=0,
        request_cost=0,
        fail_at=None,
        recv_side_effect=None,
    ):
        self.data = b"".join(recv_chunks)
        self.position = 0
        self.clock = clock_state
        self.recv_cost = recv_cost
        self.factory_cost = factory_cost
        self.request_cost = request_cost
        self.fail_at = fail_at
        self.recv_side_effect = recv_side_effect
        self.request_side_effect = request_side_effect
        self.close_side_effect = close_side_effect
        self.requests = []
        self.factory_calls = []
        self.read_sizes = []
        self.timeouts = []
        self.request_timeout = None
        self.closed = False
        self.sock = SimpleNamespace(
            recv=self._recv,
            settimeout=self.timeouts.append,
            timeout=None,
        )
        self.timeout = None

    def _recv(self, n):
        assert n == 1
        self.read_sizes.append(n)
        self.clock["now"] += self.recv_cost
        if self.fail_at is not None and self.position >= self.fail_at:
            raise OSError("injected read failure")
        chunk = self.data[self.position : self.position + n]
        self.position += len(chunk)
        if self.recv_side_effect:
            self.recv_side_effect()
        return chunk

    def request(self, method, path, body=None, headers=None):
        self.request_timeout = self.timeout
        self.requests.append((method, path, body, headers))
        self.clock["now"] += self.request_cost
        if self.request_side_effect:
            self.request_side_effect()

    def close(self):
        self.closed = True
        if self.close_side_effect:
            self.close_side_effect()

    def factory(self, host, port=443, timeout=None):
        self.factory_calls.append((host, port, timeout))
        self.timeout = timeout
        self.clock["now"] += self.factory_cost
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
    return SimpleNamespace(
        mod=mod,
        sig_state=sig_state,
        clock_state=clock_state,
        transport=lambda *args, **kwargs: TransportHarness(
            *args, clock_state=clock_state, **kwargs
        ),
    )


def _valid_headers():
    return (
        b"HTTP/1.1 200 OK\r\n"
        b"Content-Length: 12345\r\n"
        b'ETag: "abc"\r\n'
        b"Last-Modified: Wed, 21 Oct 2015 07:28:00 GMT\r\n"
        b"Accept-Ranges: bytes\r\n"
        b"\r\n"
    )


def _valid_chunks():
    hdr = _valid_headers()
    return [hdr[:32], hdr[32:], b"BODY-SENTINEL"]


def _sized_headers(size):
    prefix = b"HTTP/1.1 200 OK\r\nContent-Length: 1\r\nX-Pad: "
    suffix = b"\r\n\r\n"
    raw = prefix + b"A" * (size - len(prefix) - len(suffix)) + suffix
    assert len(raw) == size
    return raw


def test_valid_capture(cap_env):
    from validate_development_head import parse_head_evidence

    raw = _valid_headers()
    harness = cap_env.transport(_valid_chunks())
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
    assert harness.requests[0][1] == PINNED_URL.removeprefix("https://ftp.ncbi.nlm.nih.gov")
    assert harness.requests[0][2] is None
    assert harness.requests[0][3] == {"Accept-Encoding": "identity", "Connection": "close"}
    assert harness.closed is True
    assert harness.factory_calls == [("ftp.ncbi.nlm.nih.gov", 443, 15.0)]
    assert len(harness.requests) == 1
    assert harness.data[harness.position :] == b"BODY-SENTINEL"
    assert cap_env.sig_state["timers"][signal.ITIMER_REAL] == (0.0, 0.0)
    assert cap_env.sig_state["handlers"][signal.SIGALRM] == signal.SIG_DFL


@pytest.mark.parametrize(
    "url,ts,reason",
    [
        ("http://bad.example", PINNED_TS, "BAD_TARGET"),
        (PINNED_URL, "", "BAD_LABEL"),
        (PINNED_URL, "bad\x00ts", "BAD_LABEL"),
        (PINNED_URL, "bad\x80ts", "BAD_LABEL"),
        (PINNED_URL, {"not": "a timestamp"}, "BAD_LABEL"),
        (None, PINNED_TS, "BAD_TARGET"),
    ],
)
def test_preflight_refusals(cap_env, url, ts, reason):
    harness = cap_env.transport([])
    result = cap_env.mod.capture_head(url=url, observed_at=ts, connection_factory=harness.factory)
    assert result["capture_status"] == "REFUSED"
    assert result["reason"] == reason
    assert result["requests_attempted"] == 0
    assert harness.requests == []
    assert harness.factory_calls == []
    assert result["url" if reason == "BAD_TARGET" else "observed_at"] is None


def test_none_factory_refusal(cap_env):
    result = cap_env.mod.capture_head(
        url=PINNED_URL, observed_at=PINNED_TS, connection_factory=None
    )
    assert result["capture_status"] == "REFUSED"
    assert result["reason"] == "LIVE_TRANSPORT_NOT_ENABLED"
    assert result["requests_attempted"] == 0


def test_exact_65536_success(cap_env):
    from validate_development_head import parse_head_evidence

    raw = _sized_headers(65536)
    assert len(raw) == 65536
    chunks = [raw[:1000], raw[1000:]]
    harness = cap_env.transport(chunks)
    result = cap_env.mod.capture_head(
        url=PINNED_URL, observed_at=PINNED_TS, connection_factory=harness.factory
    )
    assert result["capture_status"] == "CAPTURED"
    assert result["header_bytes"] == 65536
    assert result["metadata"] == parse_head_evidence(raw, url=PINNED_URL, observed_at=PINNED_TS)
    assert harness.closed is True


def test_header_cap_65537(cap_env):
    raw = _sized_headers(65537)
    assert len(raw) == 65537
    chunks = [raw[:1000], raw[1000:]]
    harness = cap_env.transport(chunks)
    result = cap_env.mod.capture_head(
        url=PINNED_URL, observed_at=PINNED_TS, connection_factory=harness.factory
    )
    assert result["capture_status"] == "REFUSED"
    assert result["reason"] == "HEADER_CAP"
    assert result["header_bytes"] == 65536
    assert harness.closed is True
    assert harness.position == 65536
    assert len(harness.data[harness.position :]) == 1


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
    harness = cap_env.transport(chunks)
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
        (b"HTTP/1.1 100 Continue\r\n\r\n", "PARSER_REFUSAL"),
        (b"HTTP/1.1 200 OK\r\n\r\n", "PARSER_REFUSAL"),
        (
            b"HTTP/1.1 200 OK\r\nContent-Length: 1\r\nContent-Encoding: gzip\r\n\r\n",
            "ENCODING_REFUSAL",
        ),
        (
            b"HTTP/1.1 200 OK\r\nContent-Length: 1\r\nContent-Encoding: identity\r\n"
            b"Content-Encoding: identity\r\n\r\n",
            "ENCODING_REFUSAL",
        ),
        (b"HTTP/1.1 200 OK\r\nContent-Length: 0\r\n\r\n", "PARSER_REFUSAL"),
    ],
)
def test_parser_and_encoding_refusals(cap_env, raw, reason):
    harness = cap_env.transport([raw, b"NEXT-BLOCK-OR-BODY"])
    result = cap_env.mod.capture_head(
        url=PINNED_URL, observed_at=PINNED_TS, connection_factory=harness.factory
    )
    assert result["capture_status"] == "REFUSED"
    assert result["reason"] == reason
    assert result["requests_attempted"] == 1
    assert result["header_bytes"] == len(raw)
    assert harness.closed is True
    assert harness.position == len(raw)
    assert len(harness.requests) == 1
    assert result["header_record_sha256"] == hashlib.sha256(raw).hexdigest()


def test_eof_truncation(cap_env):
    raw = b"HTTP/1.1 200 OK\r\nContent-Length: 1\r\n"
    harness = cap_env.transport([raw])
    result = cap_env.mod.capture_head(
        url=PINNED_URL, observed_at=PINNED_TS, connection_factory=harness.factory
    )
    assert result["capture_status"] == "REFUSED"
    assert result["reason"] == "TRUNCATION"
    assert result["header_bytes"] == len(raw)
    assert harness.closed is True


def test_io_failure(cap_env):
    harness = cap_env.transport(_valid_chunks(), fail_at=20)
    result = cap_env.mod.capture_head(
        url=PINNED_URL, observed_at=PINNED_TS, connection_factory=harness.factory
    )
    assert result["capture_status"] == "REFUSED"
    assert result["reason"] == "IO_FAILURE"
    assert harness.closed is True
    assert base64.b64decode(result["raw_header_base64"]) == _valid_headers()[:20]
    assert result["header_record_sha256"] == hashlib.sha256(_valid_headers()[:20]).hexdigest()


def test_deadline_expired_slow_trickle(cap_env):
    raw = _valid_headers()
    chunks = [raw[:10], raw[10:20], raw[20:]]
    harness = cap_env.transport(chunks, recv_cost=0.5)
    result = cap_env.mod.capture_head(
        url=PINNED_URL, observed_at=PINNED_TS, connection_factory=harness.factory
    )
    assert result["capture_status"] == "REFUSED"
    assert result["reason"] == "DEADLINE_EXPIRED"
    assert harness.closed is True
    assert harness.position == 30
    assert base64.b64decode(result["raw_header_base64"]) == raw[:30]
    assert harness.timeouts[0] == 15.0
    assert harness.timeouts[-1] == 0.5


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
    harness = cap_env.transport([])
    result = cap_env.mod.capture_head(
        url=PINNED_URL, observed_at=PINNED_TS, connection_factory=harness.factory
    )
    assert result["capture_status"] == "REFUSED"
    assert result["reason"] == "DEADLINE_UNAVAILABLE"
    assert result["requests_attempted"] == 0


@pytest.mark.parametrize("timer", [(1.0, 0.0), (0.0, 1.0)])
def test_active_timer_refusal(cap_env, timer):
    cap_env.sig_state["timers"][signal.ITIMER_REAL] = timer
    harness = cap_env.transport([])
    result = cap_env.mod.capture_head(
        url=PINNED_URL, observed_at=PINNED_TS, connection_factory=harness.factory
    )
    assert result["capture_status"] == "REFUSED"
    assert result["reason"] == "DEADLINE_UNAVAILABLE"
    assert result["requests_attempted"] == 0
    assert cap_env.sig_state["timers"][signal.ITIMER_REAL] == timer
    assert harness.factory_calls == []


def test_request_exception(cap_env):
    def boom():
        raise OSError("req fail")

    harness = cap_env.transport([], request_side_effect=boom)
    result = cap_env.mod.capture_head(
        url=PINNED_URL, observed_at=PINNED_TS, connection_factory=harness.factory
    )
    assert result["capture_status"] == "REFUSED"
    assert result["reason"] == "IO_FAILURE"
    assert result["requests_attempted"] == 1
    assert harness.closed is True


def test_no_live_requests_on_import(cap_env):
    assert cap_env.mod.capture_head is not None
    report = cap_env.mod.capture_head(
        url=PINNED_URL, observed_at=PINNED_TS, connection_factory=None
    )
    assert report["capture_status"] == "REFUSED"
    assert report["reason"] == "LIVE_TRANSPORT_NOT_ENABLED"
    json.dumps(report)


def test_cleanup_failure_refuses_success(cap_env):
    def fail_close():
        raise OSError("close fail")

    harness = cap_env.transport(_valid_chunks(), close_side_effect=fail_close)
    result = cap_env.mod.capture_head(
        url=PINNED_URL, observed_at=PINNED_TS, connection_factory=harness.factory
    )
    assert result["capture_status"] == "REFUSED"
    assert result["reason"] == "IO_FAILURE"
    assert result["metadata"] is None


@pytest.mark.parametrize("stage", ["request", "last_byte", "parse"])
def test_late_result_never_succeeds(cap_env, monkeypatch, stage):
    raw = _valid_headers()
    harness = cap_env.transport([raw])
    if stage == "request":
        harness.request_cost = 15
    elif stage == "last_byte":

        def arrive_late():
            if harness.position == len(raw):
                cap_env.clock_state["now"] = 15

        harness.recv_side_effect = arrive_late
    else:
        parse = cap_env.mod.parse_head_evidence

        def slow_parse(*args, **kwargs):
            result = parse(*args, **kwargs)
            cap_env.clock_state["now"] = 15
            return result

        monkeypatch.setattr(cap_env.mod, "parse_head_evidence", slow_parse)
    result = cap_env.mod.capture_head(
        url=PINNED_URL, observed_at=PINNED_TS, connection_factory=harness.factory
    )
    assert result["reason"] == "DEADLINE_EXPIRED"
    assert result["metadata"] is None
    assert result["requests_attempted"] == 1
    assert base64.b64decode(result["raw_header_base64"]) == (b"" if stage == "request" else raw)
    assert harness.closed
    assert cap_env.sig_state["timers"][signal.ITIMER_REAL] == (0, 0)
    assert cap_env.sig_state["handlers"][signal.SIGALRM] == signal.SIG_DFL


def test_one_start_time_across_stages(cap_env):
    harness = cap_env.transport(_valid_chunks(), factory_cost=2, request_cost=3)
    result = cap_env.mod.capture_head(
        url=PINNED_URL, observed_at=PINNED_TS, connection_factory=harness.factory
    )
    assert result["capture_status"] == "CAPTURED"
    assert harness.factory_calls[0][2] == 15
    assert harness.request_timeout == 13
    assert set(harness.timeouts) == {10}


@pytest.mark.parametrize("failure", ["missing_api", "noncallable_api", "arming"])
def test_deadline_setup_refuses_before_factory(cap_env, monkeypatch, failure):
    sig = cap_env.mod._signal
    if failure == "missing_api":
        monkeypatch.delattr(sig, "setitimer")
    elif failure == "noncallable_api":
        monkeypatch.setattr(sig, "setitimer", None)
    else:
        original = sig.setitimer

        def broken_arm(which, seconds, interval=0):
            if seconds:
                raise OSError("cannot arm")
            return original(which, seconds, interval)

        monkeypatch.setattr(sig, "setitimer", broken_arm)
    harness = cap_env.transport([])
    result = cap_env.mod.capture_head(
        url=PINNED_URL, observed_at=PINNED_TS, connection_factory=harness.factory
    )
    assert result["reason"] == "DEADLINE_UNAVAILABLE"
    assert harness.factory_calls == []
    assert cap_env.sig_state["timers"][signal.ITIMER_REAL] == (0, 0)
    assert cap_env.sig_state["handlers"][signal.SIGALRM] == signal.SIG_DFL


def test_cleanup_does_not_hide_primary_refusal(cap_env):
    def fail_close():
        raise OSError("close failed")

    harness = cap_env.transport([b"partial"], close_side_effect=fail_close)
    result = cap_env.mod.capture_head(
        url=PINNED_URL, observed_at=PINNED_TS, connection_factory=harness.factory
    )
    assert result["reason"] == "TRUNCATION"
    assert result["metadata"] is None
    assert base64.b64decode(result["raw_header_base64"]) == b"partial"
    assert cap_env.sig_state["timers"][signal.ITIMER_REAL] == (0, 0)
    assert cap_env.sig_state["handlers"][signal.SIGALRM] == signal.SIG_DFL


def test_harness_preserves_chunks_and_advances_shared_clock():
    clock = {"now": 0}
    harness = TransportHarness([b"AB", b"C"], clock_state=clock, recv_cost=0.5)
    assert harness.sock.recv(1) == b"A"
    assert harness.sock.recv(1) == b"B"
    assert clock["now"] == 1
    assert harness.data[harness.position :] == b"C"


def test_exact_boundary_fixture_is_valid(monkeypatch):
    monkeypatch.syspath_prepend(str(SCRIPTS))
    from validate_development_head import parse_head_evidence

    assert (
        parse_head_evidence(_sized_headers(65536), url=PINNED_URL, observed_at=PINNED_TS)[
            "header_bytes"
        ]
        == 65536
    )


def test_restore_actual_previous_handler(cap_env):
    def previous(*_):
        pass

    cap_env.sig_state["handlers"][signal.SIGALRM] = previous
    harness = cap_env.transport(_valid_chunks())
    result = cap_env.mod.capture_head(
        url=PINNED_URL, observed_at=PINNED_TS, connection_factory=harness.factory
    )
    assert result["capture_status"] == "CAPTURED"
    assert cap_env.sig_state["handlers"][signal.SIGALRM] is previous


@pytest.mark.parametrize("where", ["timer", "handler"])
def test_failed_signal_cleanup_cannot_succeed(cap_env, monkeypatch, where):
    sig = cap_env.mod._signal
    if where == "timer":
        original = sig.setitimer

        def fail_cleanup(which, seconds, interval=0):
            if seconds == 0:
                raise OSError("disarm failed")
            return original(which, seconds, interval)

        monkeypatch.setattr(sig, "setitimer", fail_cleanup)
    else:
        original = sig.signal

        def fail_restore(which, handler):
            if handler == signal.SIG_DFL:
                raise OSError("restore failed")
            return original(which, handler)

        monkeypatch.setattr(sig, "signal", fail_restore)
    harness = cap_env.transport(_valid_chunks())
    result = cap_env.mod.capture_head(
        url=PINNED_URL, observed_at=PINNED_TS, connection_factory=harness.factory
    )
    assert result["capture_status"] == "REFUSED"
    assert result["reason"] == "IO_FAILURE"
    assert result["metadata"] is None


def test_slow_cleanup_cannot_succeed(cap_env):
    def late_close():
        cap_env.clock_state["now"] = 15

    harness = cap_env.transport(_valid_chunks(), close_side_effect=late_close)
    result = cap_env.mod.capture_head(
        url=PINNED_URL, observed_at=PINNED_TS, connection_factory=harness.factory
    )
    assert result["reason"] == "DEADLINE_EXPIRED"
    assert result["metadata"] is None


@pytest.mark.parametrize("where", ["factory", "read"])
def test_timeout_categories_and_prefix(cap_env, where):
    harness = cap_env.transport(_valid_chunks())

    def timeout(*args, **kwargs):
        raise TimeoutError("test timeout")

    factory = harness.factory
    if where == "factory":
        factory = timeout
        expected = b""
    else:
        original = harness.sock.recv

        def read(n):
            if harness.position == 20:
                timeout()
            return original(n)

        harness.sock.recv = read
        expected = _valid_headers()[:20]
    result = cap_env.mod.capture_head(
        url=PINNED_URL, observed_at=PINNED_TS, connection_factory=factory
    )
    assert result["reason"] == "DEADLINE_EXPIRED"
    assert base64.b64decode(result["raw_header_base64"]) == expected


def test_invalid_labels_never_echo_control_text(cap_env):
    result = cap_env.mod.capture_head(url="wrong", observed_at="bad\x00time")
    assert result["url"] is None
    assert result["observed_at"] is None


def test_unrestorable_handler_refuses_before_transport(cap_env):
    cap_env.sig_state["handlers"][signal.SIGALRM] = None
    harness = cap_env.transport([])
    result = cap_env.mod.capture_head(
        url=PINNED_URL, observed_at=PINNED_TS, connection_factory=harness.factory
    )
    assert result["reason"] == "DEADLINE_UNAVAILABLE"
    assert harness.factory_calls == []
    assert cap_env.sig_state["handlers"][signal.SIGALRM] is None


# END OF FILE
