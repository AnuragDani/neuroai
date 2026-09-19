"""Offline-reviewed capture core for a pinned development HEAD request.

This module is NOT an authorized production launcher. It performs no live
transport by default; a trusted explicit factory is required and is not
authorization proof. Outer reviewed authorization, source hashes, isolation,
memory/no-swap/output/disk controls and a hard process watchdog remain
mandatory. No completion of E2-M, usable data, training or hard runtime
isolation is implied.
"""

from __future__ import annotations

import base64
import hashlib
import signal as _real_signal
import threading as _real_threading

from validate_development_head import parse_head_evidence

# Module seams (monkeypatched by tests).
_monotonic = _real_signal.time
_signal = _real_signal
threading = _real_threading

PINNED_URL = (
    "https://ftp.ncbi.nlm.nih.gov/geo/series/GSE305nnn/GSE305146/suppl/"
    "GSE305146_seur_integr_labelled_exc_lin_PCW10_20.rda.gz"
)
PINNED_HOST = "ftp.ncbi.nlm.nih.gov"
PINNED_PORT = 443
DEADLINE_SECONDS = 15.0
MAX_HEADER_BYTES = 65536


def _refusal(
    reason: str,
    *,
    url: str | None = None,
    observed_at: str | None = None,
    requests_attempted: int = 0,
    header_bytes: int = 0,
    raw_prefix: bytes = b"",
) -> dict:
    sha = hashlib.sha256(raw_prefix).hexdigest() if raw_prefix else None
    return {
        "capture_status": "REFUSED",
        "reason": reason,
        "url": url,
        "observed_at": observed_at,
        "requests_attempted": requests_attempted,
        "header_bytes": header_bytes,
        "raw_header_base64": base64.b64encode(raw_prefix).decode("ascii"),
        "header_record_sha256": sha,
        "metadata": None,
        "body_bytes": 0,
        "scientific_gate_effect": "NONE",
    }


def _success(
    url: str,
    observed_at: str,
    raw_prefix: bytes,
    metadata: dict,
) -> dict:
    return {
        "capture_status": "CAPTURED",
        "reason": None,
        "url": url,
        "observed_at": observed_at,
        "requests_attempted": 1,
        "header_bytes": len(raw_prefix),
        "raw_header_base64": base64.b64encode(raw_prefix).decode("ascii"),
        "header_record_sha256": hashlib.sha256(raw_prefix).hexdigest(),
        "metadata": metadata,
        "body_bytes": 0,
        "scientific_gate_effect": "NONE",
    }


def _validate_labels(url: str, observed_at: str) -> str | None:
    if url != PINNED_URL:
        return "BAD_TARGET"
    if not isinstance(observed_at, str) or not observed_at:
        return "BAD_LABEL"
    for ch in observed_at:
        o = ord(ch)
        if o < 32 or 127 <= o <= 159:
            return "BAD_LABEL"
    return None


def _check_encoding(raw: bytes) -> str | None:
    """Return ENCODING_REFUSAL if Content-Encoding is non-identity or duplicated."""
    lines = raw.split(b"\r\n")
    ce_count = 0
    for line in lines:
        if line.lower().startswith(b"content-encoding:"):
            ce_count += 1
            val = line.split(b":", 1)[1].strip().lower()
            if val != b"identity":
                return "ENCODING_REFUSAL"
    if ce_count > 1:
        return "ENCODING_REFUSAL"
    return None


def _setup_deadline(remaining: float) -> bool:
    """Install SIGALRM handler and arm ITIMER_REAL. Returns True on success."""
    try:
        if not threading.current_thread().is_main():
            return False
        if not callable(_signal.getsignal) or not callable(_signal.signal):
            return False
        if not callable(_signal.getitimer) or not callable(_signal.setitimer):
            return False
        prev_timer = _signal.getitimer(_signal.ITIMER_REAL)
        if prev_timer != (0.0, 0.0) and prev_timer != (0, 0):
            return False

        def _alarm_handler(signum, frame):
            raise TimeoutError("deadline expired")

        prev_handler = _signal.signal(_signal.SIGALRM, _alarm_handler)
        _signal.setitimer(_signal.ITIMER_REAL, remaining, 0.0)
        return True
    except Exception:
        return False


def _teardown_deadline() -> None:
    """Disarm ITIMER_REAL and restore previous handler."""
    try:
        _signal.setitimer(_signal.ITIMER_REAL, 0.0, 0.0)
    except Exception:
        pass
    try:
        _signal.signal(_signal.SIGALRM, None)
    except Exception:
        pass


def capture_head(
    *,
    url: str,
    observed_at: str,
    connection_factory=None,
) -> dict:
    # Preflight: validate labels before any transport work.
    label_err = _validate_labels(url, observed_at)
    if label_err is not None:
        if label_err == "BAD_TARGET":
            return _refusal(label_err, observed_at=observed_at if isinstance(observed_at, str) else None)
        return _refusal(label_err, url=url if url == PINNED_URL else None)

    # None factory => refusal before clock/signal/transport.
    if connection_factory is None:
        return _refusal("LIVE_TRANSPORT_NOT_ENABLED", url=url, observed_at=observed_at)

    # Monotonic start and deadline.
    start = _monotonic()
    deadline = start + DEADLINE_SECONDS

    def _remaining() -> float:
        return deadline - _monotonic()

    # Signal setup before factory.
    if not _setup_deadline(_remaining()):
        return _refusal("DEADLINE_UNAVAILABLE", url=url, observed_at=observed_at)

    conn = None
    requests_attempted = 0
    raw_prefix = bytearray()
    reason: str | None = None
    metadata: dict | None = None
    cleanup_failed = False

    try:
        # Factory call.
        try:
            conn = connection_factory(PINNED_HOST, port=PINNED_PORT, timeout=_remaining())
        except Exception:
            # Factory raised; it owns cleanup of resources never handed over.
            return _refusal("IO_FAILURE", url=url, observed_at=observed_at)

        # Check deadline after factory returns.
        if _remaining() <= 0:
            reason = "DEADLINE_EXPIRED"
            try:
                conn.close()
            except Exception:
                cleanup_failed = True
            return _refusal(
                reason, url=url, observed_at=observed_at,
                header_bytes=len(raw_prefix), raw_prefix=bytes(raw_prefix),
            )

        # Set connection timeout and issue HEAD request.
        try:
            conn.timeout = _remaining()
            path = url.removeprefix(f"https://{PINNED_HOST}")
            conn.request(
                "HEAD", path, body=None,
                headers={"Accept-Encoding": "identity", "Connection": "close"},
            )
            requests_attempted = 1
        except TimeoutError:
            reason = "DEADLINE_EXPIRED"
        except OSError:
            reason = "IO_FAILURE"

        if reason is None:
            # Check deadline before reading.
            if _remaining() <= 0:
                reason = "DEADLINE_EXPIRED"
            else:
                # Read raw bytes one at a time until CRLFCRLF or cap.
                try:
                    while True:
                        if _remaining() <= 0:
                            reason = "DEADLINE_EXPIRED"
                            break
                        conn.sock.settimeout(_remaining())
                        chunk = conn.sock.recv(1)
                        if not chunk:
                            reason = "TRUNCATION"
                            break
                        raw_prefix.append(chunk[0])
                        if len(raw_prefix) >= MAX_HEADER_BYTES:
                            # Check for terminator at exactly 65536.
                            if len(raw_prefix) == MAX_HEADER_BYTES:
                                if bytes(raw_prefix[-4:]) == b"\r\n\r\n":
                                    break  # success
                                else:
                                    reason = "HEADER_CAP"
                                    break
                            else:
                                reason = "HEADER_CAP"
                                break
                        if bytes(raw_prefix[-4:]) == b"\r\n\r\n":
                            break
                except TimeoutError:
                    reason = "DEADLINE_EXPIRED"
                except OSError:
                    reason = "IO_FAILURE"

        # Final deadline check before parser.
        if reason is None and _remaining() <= 0:
            reason = "DEADLINE_EXPIRED"

        # Encoding check.
        if reason is None:
            enc_err = _check_encoding(bytes(raw_prefix))
            if enc_err is not None:
                reason = enc_err

        # Parser.
        if reason is None:
            try:
                metadata = parse_head_evidence(
                    bytes(raw_prefix), url=url, observed_at=observed_at
                )
            except ValueError:
                reason = "PARSER_REFUSAL"

        # Final deadline check after parser.
        if reason is None and _remaining() <= 0:
            reason = "DEADLINE_EXPIRED"
            metadata = None

    finally:
        # Close connection on all paths.
        if conn is not None:
            try:
                conn.close()
            except Exception:
                cleanup_failed = True
        _teardown_deadline()

    # Build result.
    if reason is None and metadata is not None:
        if cleanup_failed:
            return _refusal(
                "IO_FAILURE", url=url, observed_at=observed_at,
                requests_attempted=requests_attempted,
                header_bytes=len(raw_prefix), raw_prefix=bytes(raw_prefix),
            )
        return _success(url, observed_at, bytes(raw_prefix), metadata)

    return _refusal(
        reason, url=url, observed_at=observed_at,
        requests_attempted=requests_attempted,
        header_bytes=len(raw_prefix), raw_prefix=bytes(raw_prefix),
    )


# END OF FILE
