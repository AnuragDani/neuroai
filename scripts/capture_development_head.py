"""Capture one pinned HEAD header block through an explicit trusted transport.

No default live transport or CLI. The separately authorized launcher must verify
source hashes, TLS configuration, isolation, memory/swap/disk/output controls
and a hard process watchdog. Python signals can be delayed by C execution.
body_bytes counts application reads only; TLS/OS buffering is not measured here.
"""

import base64
import hashlib
import signal as _signal
import threading
from time import monotonic as _monotonic

from validate_development_head import parse_head_evidence

PINNED_URL = (
    "https://ftp.ncbi.nlm.nih.gov/geo/series/GSE305nnn/GSE305146/suppl/"
    "GSE305146_seur_integr_labelled_exc_lin_PCW10_20.rda.gz"
)
PINNED_HOST = "ftp.ncbi.nlm.nih.gov"
DEADLINE_SECONDS = 15.0
MAX_HEADER_BYTES = 65536


def _valid_label(value):
    return (
        isinstance(value, str)
        and bool(value)
        and not any(ord(ch) < 32 or 127 <= ord(ch) <= 159 for ch in value)
    )


def _report(reason, url, observed_at, raw=b"", attempts=0, metadata=None):
    return {
        "capture_status": "REFUSED" if reason else "CAPTURED",
        "reason": reason,
        "url": url,
        "observed_at": observed_at,
        "requests_attempted": attempts,
        "header_bytes": len(raw),
        "raw_header_base64": base64.b64encode(raw).decode("ascii"),
        "header_record_sha256": hashlib.sha256(raw).hexdigest() if raw else None,
        "metadata": None if reason else metadata,
        "body_bytes": 0,
        "scientific_gate_effect": "NONE",
    }


def capture_head(*, url: str, observed_at: str, connection_factory=None) -> dict:
    """Return captured metadata or a bounded-category refusal, never authorization.

    The explicit factory constructs an HTTPSConnection-like object without I/O;
    request() performs connection/TLS/send. A factory that raises before returning
    owns cleanup of resources it never handed over. The launcher must supply a
    verified TLS transport without proxy/retry behavior. No arbitrary URL is allowed.
    """
    safe_url = url if isinstance(url, str) and url == PINNED_URL else None
    safe_time = observed_at if _valid_label(observed_at) else None
    if safe_url is None or safe_time is None:
        return _report("BAD_TARGET" if safe_url is None else "BAD_LABEL", safe_url, safe_time)
    if connection_factory is None:
        return _report("LIVE_TRANSPORT_NOT_ENABLED", safe_url, safe_time)

    deadline = _monotonic() + DEADLINE_SECONDS

    def remaining():
        seconds = deadline - _monotonic()
        if seconds <= 0:
            raise TimeoutError("capture deadline")
        return seconds

    # Fail before transport if another timer/handler cannot safely be preserved.
    try:
        if (
            threading.current_thread() is not threading.main_thread()
            or not all(
                callable(getattr(_signal, name, None))
                for name in ("getsignal", "signal", "getitimer", "setitimer")
            )
            or _signal.getitimer(_signal.ITIMER_REAL) != (0, 0)
        ):
            return _report("DEADLINE_UNAVAILABLE", safe_url, safe_time)
        previous_handler = _signal.getsignal(_signal.SIGALRM)
        if not callable(previous_handler) and previous_handler not in (
            _signal.SIG_DFL,
            _signal.SIG_IGN,
        ):
            return _report("DEADLINE_UNAVAILABLE", safe_url, safe_time)
    except Exception:
        return _report("DEADLINE_UNAVAILABLE", safe_url, safe_time)

    def alarm(signum, frame):
        raise TimeoutError("capture deadline")

    conn = None
    attempts = 0
    raw = bytearray()
    reason = None
    metadata = None
    cleanup_reason = None
    try:
        try:
            _signal.signal(_signal.SIGALRM, alarm)
            _signal.setitimer(_signal.ITIMER_REAL, remaining())
        except TimeoutError:
            reason = "DEADLINE_EXPIRED"
        except Exception:
            reason = "DEADLINE_UNAVAILABLE"

        if reason is None:
            try:
                conn = connection_factory(PINNED_HOST, port=443, timeout=remaining())
                conn.timeout = remaining()
                attempts = 1
                conn.request(
                    "HEAD",
                    url.removeprefix(f"https://{PINNED_HOST}"),
                    body=None,
                    headers={"Accept-Encoding": "identity", "Connection": "close"},
                )
                remaining()
                # ponytail: recv(1) avoids application-level body overread at this
                # fixed 64 KiB ceiling; optimize only with equivalent byte-bound proof.
                while len(raw) < MAX_HEADER_BYTES:
                    conn.sock.settimeout(remaining())
                    chunk = conn.sock.recv(1)
                    raw.extend(chunk)
                    remaining()
                    if not chunk:
                        reason = "TRUNCATION"
                        break
                    if raw.endswith(b"\r\n\r\n"):
                        break
                else:
                    reason = "HEADER_CAP"

                if reason is None:
                    try:
                        metadata = parse_head_evidence(
                            bytes(raw), url=safe_url, observed_at=safe_time
                        )
                    except ValueError:
                        reason = "PARSER_REFUSAL"
                    if reason is None:
                        encodings = [
                            line.split(b":", 1)[1].strip(b" \t").lower()
                            for line in raw.split(b"\r\n")
                            if line.lower().startswith(b"content-encoding:")
                        ]
                        if encodings not in ([], [b"identity"]):
                            reason = "ENCODING_REFUSAL"
                        remaining()
            except TimeoutError:
                reason = "DEADLINE_EXPIRED"
            except OSError:
                reason = "IO_FAILURE"
    finally:
        # Restore after partial setup too. Cleanup errors cannot certify success
        # or overwrite a primary refusal; KeyboardInterrupt/SystemExit propagate.
        cleanups = []
        if conn is not None:
            cleanups.append(conn.close)
        cleanups.extend(
            (
                lambda: _signal.setitimer(_signal.ITIMER_REAL, 0),
                lambda: _signal.signal(_signal.SIGALRM, previous_handler),
            )
        )
        for cleanup in cleanups:
            try:
                cleanup()
            except TimeoutError:
                cleanup_reason = cleanup_reason or "DEADLINE_EXPIRED"
            except Exception:
                cleanup_reason = cleanup_reason or "IO_FAILURE"

    if reason is None:
        reason = cleanup_reason
        if reason is None:
            try:
                remaining()
            except TimeoutError:
                reason = "DEADLINE_EXPIRED"
    return _report(reason, safe_url, safe_time, bytes(raw), attempts, metadata)
