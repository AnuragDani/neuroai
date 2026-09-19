import hashlib
import json
import os
import sys
import time
import unittest
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import launcher_head_capture as lhc
from validate_development_head import parse_head_evidence

CONTRACT_SHA = "9a13d8beafa5e00d81f8f985649a6a466c6b4fe3ebf008206f840c32316113f2"
NOTE_SHA = "66b1d8158f5b6c4260085cddb736db2d59de9df610e5dcac5ccfc2c4f63b18b9"
CORE_SHA = "335d35c51b27d48704eaad62a695d74e6e91f456e3148b15abe8d3aff846029c"
PARSER_SHA = "c761489202fdbfaba5153f7a508aefa19028cf87f681bd473382c6c4c713ac9d"
IMAGE_ID = "sha256:f462f91ca01ce7751254e3b528af0fccc3746f158a4a7a73675186718307e47e"


def make_valid_contract():
    return {
        "schema_version": 1,
        "planning_revision": "2026-09-14",
        "status": "SOURCE_UNRESOLVED",
        "phase": "E2_OFFLINE_CONTRACT",
        "object_inspection_authorized": False,
        "selected_target": "GSE305146_seur_integr_labelled_exc_lin_PCW10_20.rda.gz",
        "intended_scope": "Lattke excitatory-lineage PCW10-20 development donors; actual coverage unverified",
        "declared_listing_size": "7.6G (rounded, not an exact byte measurement)",
        "format_declared": "gzip-compressed R workspace; actual serialized classes unknown",
        "candidate_payload_url": "https://ftp.ncbi.nlm.nih.gov/geo/series/GSE305nnn/GSE305146/suppl/GSE305146_seur_integr_labelled_exc_lin_PCW10_20.rda.gz",
        "candidate_url_basis": "Derived from the pinned source note's directory and exact filename; not a new HTTP observation",
        "exact_payload_url": None,
        "exact_payload_bytes": None,
        "publisher_payload_checksum": None,
        "expected_decoded_bytes": None,
        "expected_peak_memory_bytes": None,
        "source_evidence": {
            "path": "docs/PAIRED_MULTIOME_REMAINING_EVIDENCE_2026-09-08.md",
            "sha256": NOTE_SHA
        },
        "reader_proof": {
            "image_id": "sha256:264df259ebb2fa4ff2a3db6d346ec273e18d4c84af727b1cc4b39065a9e8edbb",
            "r_version": "4.6.1",
            "matrix_version": "1.7.6",
            "tested_serialization": "saveRDS/readRDS of a 392-byte .rds fixture; not save/load of a .rda workspace",
            "tested_classes": ["list", "dgCMatrix", "data.frame"],
            "fixture_report_sha256": "1cf56325eb4f08c86d11661b59ec9985d9300e18a1f9a738c60fed57c9b99813",
            "not_proven": [".rda workspace loading", "Seurat", "ChromatinAssay", "real-object memory fit", "real raw ATAC assay"]
        },
        "current_object_permissions": {
            "network_bytes": 0,
            "decoded_bytes": 0,
            "output_bytes": 0,
            "execution_seconds": 0,
            "training_allowed": False
        },
        "single_next_action_proposal": {
            "status": "REQUIRES_SEPARATE_SCOPE_APPROVAL",
            "purpose": "Observe candidate payload status and available size/validator headers without reading the object body; supersedes the unexecuted listing GET",
            "method": "HEAD",
            "url": "https://ftp.ncbi.nlm.nih.gov/geo/series/GSE305nnn/GSE305146/suppl/GSE305146_seur_integr_labelled_exc_lin_PCW10_20.rda.gz",
            "maximum_requests": 1,
            "redirects": 0,
            "retries": 0,
            "maximum_response_header_bytes": 65536,
            "maximum_response_body_bytes": 0,
            "maximum_decoded_bytes": 0,
            "maximum_retained_output_bytes": 1048576,
            "maximum_process_tree_memory_bytes": 268435456,
            "maximum_swap_bytes": 0,
            "maximum_wall_seconds": 15,
            "minimum_host_free_disk_bytes": 10737418240,
            "controls": "Proposed pinned cached Python in an inspected non-root container; offline-tested aggregate header cap and absolute deadline; HEAD only with identity HTTP encoding and no body reads, redirects or Range fallback; no host-data mounts; refuse before request if controls are unproven",
            "preservation": "New output directory only; preserve prior evidence and downloaded R archive; no cache/user-data deletion",
            "stop_conditions": ["non-200 or redirect", "deadline or header limit", "missing/invalid/non-positive Content-Length", "source evidence changed", "required controls unavailable"],
            "optional_observations": ["ETag", "Last-Modified", "Accept-Ranges", "publisher checksum if explicitly supplied; never infer one from validators"],
            "evidence_semantics": "Save URL/time/status/headers and a locally computed header-record SHA-256. Content-Length, if valid, is server-declared GET representation length, not measured payload bytes, decoded size or memory. Optional missing headers remain unknown; validators/header hashes are not payload checksums; Accept-Ranges does not guarantee a future partial response.",
            "after_success": "E2-R offline target-reader/resource planning only. Source observations do not authorize package installation, fixture execution, GET/Range, object loading or training.",
            "after_failure": "Record SOURCE_UNRESOLVED and the exact missing field/control or request failure, with a local header-record hash if headers were received; no retry or source substitution"
        },
        "target_reader_resource_gate": {
            "status": "NOT_RUN",
            "offline_proposal_minutes": 30,
            "network_install_object_bytes_authorized": 0,
            "maximum_proposed_fixture_bytes": 1048576,
            "required_reader_proof": "Applicable save/load .rda workspace and Seurat/ChromatinAssay extraction, or demonstrated equivalent narrow reader; exact sparse counts, IDs and metadata; unexpected classes refuse. Cost missing package assets before acquisition; generic E1 proof is preserved but insufficient.",
            "required_resource_proposal": "Separate numeric transfer, decoded, retained/temporary disk, process-tree memory/swap and wall caps, current host headroom, evidence-backed full-load estimates and enforceable stop controls. Preserve ledgers and specify class-fixture/dependency allocation or amendment; do not infer memory from compressed length or reset setup budgets.",
            "stop_rule": "No defensible resource contract yields RESOURCE_UNRESOLVED; missing class support stays explicitly unproven. Installation or runtime setting changes require their own reviewed exact authorization before execution. A real load additionally requires applicable fixture proof and its reviewed exact acquisition/inspection contract.",
            "forbidden_shortcuts": ["64 KiB prefix/Range probe as assay proof", "compressed bytes below RAM cap as memory-fit proof", "OOM as proof of missing assay", "automatic alternate object or retry"]
        },
        "scientific_acceptance_requirements_unchanged": [
            "paired raw RNA and measured ATAC counts with exact retained barcode/donor join",
            "release and QC/count-stage semantics",
            "age/class support and specimen provenance",
            "genome build, interval coordinates and count units",
            "exact common measured regions; never zero-fill unmatched peaks",
            "feature-selection provenance including discovery donors/labels; cohort-wide cluster peaks are not automatically label-independent or train-fold-only, even if disclosed",
            "post-QC donor/class support for five repeated five-fold internal evaluation and inner validation; two donors per class are insufficient and 13+13 is external margin context, not a development minimum",
            "separate development, external and cross-cohort decisions"
        ]
    }


def make_valid_note():
    return "# PAIRED_MULTIOME_REMAINING_EVIDENCE_2026-09-08\n\nEvidence note.\n"


def make_valid_core():
    return '"""Capture core."""\nimport base64\nimport hashlib\nimport signal as _signal\nimport threading\nfrom time import monotonic as _monotonic\n\nfrom validate_development_head import parse_head_evidence\n\nPINNED_URL = (\n    "https://ftp.ncbi.nlm.nih.gov/geo/series/GSE305nnn/GSE305146/suppl/"\n    "GSE305146_seur_integr_labelled_exc_lin_PCW10_20.rda.gz"\n)\nPINNED_HOST = "ftp.ncbi.nlm.nih.gov"\nDEADLINE_SECONDS = 15.0\nMAX_HEADER_BYTES = 65536\n\n\ndef _valid_label(value):\n    return (\n        isinstance(value, str)\n        and bool(value)\n        and not any(ord(ch) < 32 or 127 <= ord(ch) <= 159 for ch in value)\n    )\n\n\ndef _report(reason, url, observed_at, raw=b"", attempts=0, metadata=None):\n    return {\n        "capture_status": "REFUSED" if reason else "CAPTURED",\n        "reason": reason,\n        "url": url,\n        "observed_at": observed_at,\n        "requests_attempted": attempts,\n        "header_bytes": len(raw),\n        "raw_header_base64": base64.b64encode(raw).decode("ascii"),\n        "header_record_sha256": hashlib.sha256(raw).hexdigest() if raw else None,\n        "metadata": None if reason else metadata,\n        "body_bytes": 0,\n        "scientific_gate_effect": "NONE",\n    }\n\n\ndef capture_head(*, url: str, observed_at: str, connection_factory=None) -> dict:\n    safe_url = url if isinstance(url, str) and url == PINNED_URL else None\n    safe_time = observed_at if _valid_label(observed_at) else None\n    if safe_url is None or safe_time is None:\n        return _report("BAD_TARGET" if safe_url is None else "BAD_LABEL", safe_url, safe_time)\n    if connection_factory is None:\n        return _report("LIVE_TRANSPORT_NOT_ENABLED", safe_url, safe_time)\n\n    deadline = _monotonic() + DEADLINE_SECONDS\n\n    def remaining():\n        seconds = deadline - _monotonic()\n        if seconds <= 0:\n            raise TimeoutError("capture deadline")\n        return seconds\n\n    try:\n        if (\n            threading.current_thread() is not threading.main_thread()\n            or not all(\n                callable(getattr(_signal, name, None))\n                for name in ("getsignal", "signal", "getitimer", "setitimer")\n            )\n            or _signal.getitimer(_signal.ITIMER_REAL) != (0, 0)\n        ):\n            return _report("DEADLINE_UNAVAILABLE", safe_url, safe_time)\n        previous_handler = _signal.getsignal(_signal.SIGALRM)\n        if not callable(previous_handler) and previous_handler not in (\n            _signal.SIG_DFL,\n            _signal.SIG_IGN,\n        ):\n            return _report("DEADLINE_UNAVAILABLE", safe_url, safe_time)\n    except Exception:\n        return _report("DEADLINE_UNAVAILABLE", safe_url, safe_time)\n\n    def alarm(signum, frame):\n        raise TimeoutError("capture deadline")\n\n    conn = None\n    attempts = 0\n    raw = bytearray()\n    reason = None\n    metadata = None\n    cleanup_reason = None\n    try:\n        try:\n            _signal.signal(_signal.SIGALRM, alarm)\n            _signal.setitimer(_signal.ITIMER_REAL, remaining())\n        except TimeoutError:\n            reason = "DEADLINE_EXPIRED"\n        except Exception:\n            reason = "DEADLINE_UNAVAILABLE"\n\n        if reason is None:\n            try:\n                conn = connection_factory(PINNED_HOST, port=443, timeout=remaining())\n                conn.timeout = remaining()\n                attempts = 1\n                conn.request(\n                    "HEAD",\n                    url.removeprefix(f"https://{PINNED_HOST}"),\n                    body=None,\n                    headers={"Accept-Encoding": "identity", "Connection": "close"},\n                )\n                remaining()\n                while len(raw) < MAX_HEADER_BYTES:\n                    conn.sock.settimeout(remaining())\n                    chunk = conn.sock.recv(1)\n                    raw.extend(chunk)\n                    remaining()\n                    if not chunk:\n                        reason = "TRUNCATION"\n                        break\n                    if raw.endswith(b"\\r\\n\\r\\n"):\n                        break\n                else:\n                    reason = "HEADER_CAP"\n\n                if reason is None:\n                    try:\n                        metadata = parse_head_evidence(\n                            bytes(raw), url=safe_url, observed_at=safe_time\n                        )\n                    except ValueError:\n                        reason = "PARSER_REFUSAL"\n                    if reason is None:\n                        encodings = [\n                            line.split(b":", 1)[1].strip(b" \\t").lower()\n                            for line in raw.split(b"\\r\\n")\n                            if line.lower().startswith(b"content-encoding:")\n                        ]\n                        if encodings not in ([], [b"identity"]):\n                            reason = "ENCODING_REFUSAL"\n                        remaining()\n            except TimeoutError:\n                reason = "DEADLINE_EXPIRED"\n            except OSError:\n                reason = "IO_FAILURE"\n    finally:\n        cleanups = []\n        if conn is not None:\n            cleanups.append(conn.close)\n        cleanups.extend(\n            (\n                lambda: _signal.setitimer(_signal.ITIMER_REAL, 0),\n                lambda: _signal.signal(_signal.SIGALRM, previous_handler),\n            )\n        )\n        for cleanup in cleanups:\n            try:\n                cleanup()\n            except TimeoutError:\n                cleanup_reason = cleanup_reason or "DEADLINE_EXPIRED"\n            except Exception:\n                cleanup_reason = cleanup_reason or "IO_FAILURE"\n\n    if reason is None:\n        reason = cleanup_reason\n        if reason is None:\n            try:\n                remaining()\n            except TimeoutError:\n                reason = "DEADLINE_EXPIRED"\n    return _report(reason, safe_url, safe_time, bytes(raw), attempts, metadata)\n'


def make_valid_parser():
    return '"""Validate one captured HTTP/1.x header block; never make a network request."""\n\nimport hashlib\nimport re\n\nMAX_BYTES = 65536\nMAX_CL_DIGITS = 19\nMAX_CL_VALUE = 2**63 - 1\n\n\ndef _validate_label(value: str, name: str) -> None:\n    if not isinstance(value, str) or not value:\n        raise ValueError(f"{name} must be a non-empty string")\n    if any(ord(c) < 32 or 127 <= ord(c) <= 159 for c in value):\n        raise ValueError(f"{name} contains control characters")\n\n\ndef _parse_content_length(value: str) -> int:\n    if not value:\n        raise ValueError("Content-Length is blank")\n    if len(value) > MAX_CL_DIGITS:\n        raise ValueError("Content-Length has excessive digits")\n    if not value.isascii() or not value.isdigit():\n        raise ValueError("Content-Length contains non-ASCII digits or invalid characters")\n    n = int(value)\n    if n < 1:\n        raise ValueError("Content-Length must be positive")\n    if n > MAX_CL_VALUE:\n        raise ValueError("Content-Length exceeds maximum")\n    return n\n\n\ndef parse_head_evidence(raw_headers: bytes, *, url: str, observed_at: str) -> dict:\n    if not isinstance(raw_headers, bytes):\n        raise ValueError("raw_headers must be bytes")\n    if len(raw_headers) > MAX_BYTES:\n        raise ValueError("raw_headers exceeds maximum size")\n    _validate_label(url, "url")\n    _validate_label(observed_at, "observed_at")\n\n    end = raw_headers.find(b"\\r\\n\\r\\n")\n    if end < 0:\n        raise ValueError("missing final CRLF CRLF terminator")\n    if end != len(raw_headers) - 4:\n        raise ValueError("trailing bytes after headers")\n\n    lines = raw_headers[:end].split(b"\\r\\n")\n    status = re.fullmatch(rb"HTTP/1\\.[01] ([0-9]{3}) [\\t\\x20-\\x7e\\x80-\\xff]*", lines[0])\n    if status is None:\n        raise ValueError("malformed status line")\n    http_status = int(status[1])\n    if http_status != 200:\n        raise ValueError(f"non-200 status: {http_status}")\n\n    headers: dict[str, list[str]] = {}\n    for line in lines[1:]:\n        if not line:\n            raise ValueError("empty header line")\n        if line.startswith(b" ") or line.startswith(b"\\t"):\n            raise ValueError("obsolete folded header")\n        if b"\\r" in line or b"\\n" in line:\n            raise ValueError("bare LF or CR in header")\n        if b":" not in line:\n            raise ValueError("malformed header line")\n        name_bytes, value_bytes = line.split(b":", 1)\n        if re.fullmatch(rb"[!#$%&'*+\\-.^_`|~0-9A-Za-z]+", name_bytes) is None:\n            raise ValueError(f"invalid header name: {name_bytes!r}")\n        name = name_bytes.decode("ascii")\n        value = value_bytes.decode("latin-1").strip(" \\t")\n        if any((ord(c) < 32 and c != "\\t") or ord(c) == 127 for c in value):\n            raise ValueError(f"control character in header value: {name!r}")\n        headers.setdefault(name.lower(), []).append(value)\n\n    if "transfer-encoding" in headers:\n        raise ValueError("Transfer-Encoding is not allowed")\n\n    cl_values = headers.get("content-length")\n    if cl_values is None:\n        raise ValueError("missing Content-Length")\n    if len(cl_values) > 1:\n        raise ValueError("duplicate Content-Length")\n    if "," in cl_values[0]:\n        raise ValueError("Content-Length contains comma list")\n    declared_payload_bytes = _parse_content_length(cl_values[0])\n\n    def _single(name: str) -> str | None:\n        vals = headers.get(name)\n        if vals is None:\n            return None\n        if len(vals) > 1:\n            raise ValueError(f"duplicate {name} header")\n        return vals[0]\n\n    return {\n        "record_kind": "development_head_metadata",\n        "status": "SOURCE_METADATA_OBSERVED",\n        "url": url,\n        "observed_at": observed_at,\n        "http_status": 200,\n        "header_record_sha256": hashlib.sha256(raw_headers).hexdigest(),\n        "header_bytes": len(raw_headers),\n        "declared_payload_bytes": declared_payload_bytes,\n        "etag": _single("etag"),\n        "last_modified": _single("last-modified"),\n        "accept_ranges": _single("accept-ranges"),\n        "publisher_payload_checksum": None,\n        "body_bytes": 0,\n        "scientific_gate_effect": "NONE",\n    }\n'


class TestLauncherHeadCapture(unittest.TestCase):
    def setUp(self):
        self.contract = make_valid_contract()
        self.note = make_valid_note()
        self.core = make_valid_core()
        self.parser = make_valid_parser()
        self.image_id = IMAGE_ID
        self.output_dir = Path("/tmp/p22-test-output")

    def _write_files(self, tmpdir):
        contract_path = tmpdir / "contract.json"
        note_path = tmpdir / "note.md"
        core_path = tmpdir / "core.py"
        parser_path = tmpdir / "parser.py"
        contract_path.write_text(json.dumps(self.contract))
        note_path.write_text(self.note)
        core_path.write_text(self.core)
        parser_path.write_text(self.parser)
        return contract_path, note_path, core_path, parser_path

    def test_preflight_source_hash_mismatch(self):
        with mock.patch.object(lhc, "verify_source_hashes") as mock_verify:
            mock_verify.return_value = False
            result = lhc.run_launcher(
                contract_path=Path("/tmp/contract.json"),
                note_path=Path("/tmp/note.md"),
                core_path=Path("/tmp/core.py"),
                parser_path=Path("/tmp/parser.py"),
                image_id=self.image_id,
                output_dir=self.output_dir,
                observed_at="2026-09-14T12:00:00Z",
                live_authorized=False,
            )
            self.assertEqual(result["status"], "REFUSED")
            self.assertIn("SOURCE_HASH_MISMATCH", result["reason"])

    def test_default_live_refusal(self):
        with mock.patch.object(lhc, "verify_source_hashes", return_value=True):
            with mock.patch.object(lhc, "verify_code_pins", return_value=True):
                with mock.patch.object(lhc, "verify_image", return_value=True):
                    result = lhc.run_launcher(
                        contract_path=Path("/tmp/contract.json"),
                        note_path=Path("/tmp/note.md"),
                        core_path=Path("/tmp/core.py"),
                        parser_path=Path("/tmp/parser.py"),
                        image_id=self.image_id,
                        output_dir=self.output_dir,
                        observed_at="2026-09-14T12:00:00Z",
                        live_authorized=False,
                    )
                    self.assertEqual(result["status"], "REFUSED")
                    self.assertIn("LIVE_NOT_AUTHORIZED", result["reason"])

    def test_offline_synthetic_success(self):
        with mock.patch.object(lhc, "verify_source_hashes", return_value=True):
            with mock.patch.object(lhc, "verify_code_pins", return_value=True):
                with mock.patch.object(lhc, "verify_image", return_value=True):
                    with mock.patch.object(lhc, "capture_head") as mock_capture:
                        mock_capture.return_value = {
                            "capture_status": "CAPTURED",
                            "reason": None,
                            "url": lhc.PINNED_URL,
                            "observed_at": "2026-09-14T12:00:00Z",
                            "requests_attempted": 1,
                            "header_bytes": 100,
                            "raw_header_base64": "test",
                            "header_record_sha256": "abc123",
                            "metadata": {"status": "SOURCE_METADATA_OBSERVED"},
                            "body_bytes": 0,
                            "scientific_gate_effect": "NONE",
                        }
                        result = lhc.run_launcher(
                            contract_path=Path("/tmp/contract.json"),
                            note_path=Path("/tmp/note.md"),
                            core_path=Path("/tmp/core.py"),
                            parser_path=Path("/tmp/parser.py"),
                            image_id=self.image_id,
                            output_dir=self.output_dir,
                            observed_at="2026-09-14T12:00:00Z",
                            live_authorized=True,
                            synthetic=True,
                        )
                        self.assertEqual(result["status"], "CAPTURED")
                        self.assertEqual(result["capture_status"], "CAPTURED")

    def test_output_overrun_refusal(self):
        with mock.patch.object(lhc, "verify_source_hashes", return_value=True):
            with mock.patch.object(lhc, "verify_code_pins", return_value=True):
                with mock.patch.object(lhc, "verify_image", return_value=True):
                    with mock.patch.object(lhc, "capture_head") as mock_capture:
                        mock_capture.return_value = {
                            "capture_status": "CAPTURED",
                            "reason": None,
                            "url": lhc.PINNED_URL,
                            "observed_at": "2026-09-14T12:00:00Z",
                            "requests_attempted": 1,
                            "header_bytes": 100,
                            "raw_header_base64": "test",
                            "header_record_sha256": "abc123",
                            "metadata": {"status": "SOURCE_METADATA_OBSERVED"},
                            "body_bytes": 0,
                            "scientific_gate_effect": "NONE",
                        }
                        with mock.patch.object(lhc, "write_output", side_effect=OSError("disk full")):
                            result = lhc.run_launcher(
                                contract_path=Path("/tmp/contract.json"),
                                note_path=Path("/tmp/note.md"),
                                core_path=Path("/tmp/core.py"),
                                parser_path=Path("/tmp/parser.py"),
                                image_id=self.image_id,
                                output_dir=self.output_dir,
                                observed_at="2026-09-14T12:00:00Z",
                                live_authorized=True,
                                synthetic=True,
                            )
                            self.assertEqual(result["status"], "REFUSED")
                            self.assertIn("OUTPUT_FAILURE", result["reason"])

    def test_deadline_exceeded(self):
        with mock.patch.object(lhc, "verify_source_hashes", return_value=True):
            with mock.patch.object(lhc, "verify_code_pins", return_value=True):
                with mock.patch.object(lhc, "verify_image", return_value=True):
                    with mock.patch.object(lhc, "capture_head") as mock_capture:
                        mock_capture.return_value = {
                            "capture_status": "REFUSED",
                            "reason": "DEADLINE_EXPIRED",
                            "url": lhc.PINNED_URL,
                            "observed_at": "2026-09-14T12:00:00Z",
                            "requests_attempted": 1,
                            "header_bytes": 0,
                            "raw_header_base64": "",
                            "header_record_sha256": None,
                            "metadata": None,
                            "body_bytes": 0,
                            "scientific_gate_effect": "NONE",
                        }
                        result = lhc.run_launcher(
                            contract_path=Path("/tmp/contract.json"),
                            note_path=Path("/tmp/note.md"),
                            core_path=Path("/tmp/core.py"),
                            parser_path=Path("/tmp/parser.py"),
                            image_id=self.image_id,
                            output_dir=self.output_dir,
                            observed_at="2026-09-14T12:00:00Z",
                            live_authorized=True,
                            synthetic=True,
                        )
                        self.assertEqual(result["status"], "REFUSED")
                        self.assertEqual(result["reason"], "DEADLINE_EXPIRED")

    def test_container_cleanup_failure(self):
        with mock.patch.object(lhc, "verify_source_hashes", return_value=True):
            with mock.patch.object(lhc, "verify_code_pins", return_value=True):
                with mock.patch.object(lhc, "verify_image", return_value=True):
                    with mock.patch.object(lhc, "capture_head") as mock_capture:
                        mock_capture.return_value = {
                            "capture_status": "CAPTURED",
                            "reason": None,
                            "url": lhc.PINNED_URL,
                            "observed_at": "2026-09-14T12:00:00Z",
                            "requests_attempted": 1,
                            "header_bytes": 100,
                            "raw_header_base64": "test",
                            "header_record_sha256": "abc123",
                            "metadata": {"status": "SOURCE_METADATA_OBSERVED"},
                            "body_bytes": 0,
                            "scientific_gate_effect": "NONE",
                        }
                        with mock.patch.object(lhc, "cleanup_container", side_effect=OSError("cleanup failed")):
                            result = lhc.run_launcher(
                                contract_path=Path("/tmp/contract.json"),
                                note_path=Path("/tmp/note.md"),
                                core_path=Path("/tmp/core.py"),
                                parser_path=Path("/tmp/parser.py"),
                                image_id=self.image_id,
                                output_dir=self.output_dir,
                                observed_at="2026-09-14T12:00:00Z",
                                live_authorized=True,
                                synthetic=True,
                            )
                            self.assertEqual(result["status"], "REFUSED")
                            self.assertIn("CLEANUP_FAILURE", result["reason"])

    def test_unchanged_scientific_gates(self):
        with mock.patch.object(lhc, "verify_source_hashes", return_value=True):
            with mock.patch.object(lhc, "verify_code_pins", return_value=True):
                with mock.patch.object(lhc, "verify_image", return_value=True):
                    with mock.patch.object(lhc, "capture_head") as mock_capture:
                        mock_capture.return_value = {
                            "capture_status": "CAPTURED",
                            "reason": None,
                            "url": lhc.PINNED_URL,
                            "observed_at": "2026-09-14T12:00:00Z",
                            "requests_attempted": 1,
                            "header_bytes": 100,
                            "raw_header_base64": "test",
                            "header_record_sha256": "abc123",
                            "metadata": {"status": "SOURCE_METADATA_OBSERVED"},
                            "body_bytes": 0,
                            "scientific_gate_effect": "NONE",
                        }
                        result = lhc.run_launcher(
                            contract_path=Path("/tmp/contract.json"),
                            note_path=Path("/tmp/note.md"),
                            core_path=Path("/tmp/core.py"),
                            parser_path=Path("/tmp/parser.py"),
                            image_id=self.image_id,
                            output_dir=self.output_dir,
                            observed_at="2026-09-14T12:00:00Z",
                            live_authorized=True,
                            synthetic=True,
                        )
                        self.assertEqual(result["scientific_gate_effect"], "NONE")


if __name__ == "__main__":
    unittest.main()
