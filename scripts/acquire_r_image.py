#!/usr/bin/env python
"""Acquire only the pinned R image; validate before creating an offline Docker archive.

No Docker calls, extraction, package installation, dataset reads, or retries.
The archive has uncompressed layers: reserve three copies plus 256 MiB overhead
inside the 6 GiB disk ceiling (archive, Docker import temporary files, layer store).
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import resource
import shutil
import signal
import tarfile
import time
import urllib.error
import urllib.request
import zlib
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/local_r_reader_acquisition.json"
CONFIG_SHA256 = "sha256:b824d6e90667f9fe7ed7bbf0f16fe6db0d6d6345e563625ae2aa6ad9728c7806"
REGISTRY = "https://registry-1.docker.io/v2/library/r-base/"
AUTH = (
    "https://auth.docker.io/token?service=registry.docker.io&scope=repository:library/r-base:pull"
)
NETWORK_LIMIT = 2 * 1024**3
DECODED_LIMIT = (6 * 1024**3 - 256 * 1024**2) // 3
MIN_FREE = 10 * 1024**3
CHUNK = 1024**2
SECONDS = 480


def sha(raw):
    return "sha256:" + hashlib.sha256(raw).hexdigest()


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def check_redirect(url):
    parts = urlsplit(url)
    allowed = {"production.cloudflare.docker.com", "production.cloudfront.docker.com"}
    if (
        parts.scheme != "https"
        or parts.hostname not in allowed
        or parts.username
        or parts.password
        or parts.port not in (None, 443)
        or parts.fragment
    ):
        raise ValueError("REDIRECT_REFUSED: " + str(parts.hostname))


def response(opener, url, report, token=None):
    headers = {"Accept-Encoding": "identity"}
    if token:
        headers["Authorization"] = "Bearer " + token
    report["requests"] += 1
    request = urllib.request.Request(url, headers=headers)
    try:
        result = opener.open(request, timeout=20)
    except urllib.error.HTTPError as error:
        location = error.headers.get("Location")
        status = error.code
        error.close()
        if status not in (302, 307) or not location or not url.startswith(REGISTRY + "blobs/"):
            raise ValueError("HTTP_REFUSAL: " + str(status)) from None
        check_redirect(location)
        report["redirect_hosts"].append(urlsplit(location).hostname)
        report["requests"] += 1
        # Deliberately construct a new request: never forward the registry bearer.
        result = opener.open(
            urllib.request.Request(location, headers={"Accept-Encoding": "identity"}), timeout=20
        )
    if result.status != 200 or result.headers.get("Content-Encoding", "identity") != "identity":
        result.close()
        raise ValueError("HTTP_RESPONSE_REFUSED")
    return result


def metadata(opener, url, report, token=None, digest=None):
    raw = bytearray()
    with response(opener, url, report, token) as stream:
        while len(raw) < 65537:
            chunk = stream.read1(min(4096, 65537 - len(raw)))
            if not chunk:
                break
            raw.extend(chunk)
            report["network_bytes"] += len(chunk)
    if len(raw) > 65536 or report["network_bytes"] > NETWORK_LIMIT:
        raise ValueError("METADATA_LIMIT")
    if digest and sha(raw) != digest:
        raise ValueError("METADATA_HASH_MISMATCH")
    return bytes(raw), json.loads(raw)


def decode_layer(stream, output, digest, size, report, *, decoded_limit=DECODED_LIMIT):
    """Stream one gzip member; charge bytes before writes and reject extra members."""
    compressed, expanded = hashlib.sha256(), hashlib.sha256()
    decoder = zlib.decompressobj(16 + zlib.MAX_WBITS)
    received = 0
    with output.open("xb") as target:
        while True:
            raw = stream.read1(min(CHUNK, size + 1 - received))
            if not raw:
                break
            received += len(raw)
            report["network_bytes"] += len(raw)
            if received > size or report["network_bytes"] > NETWORK_LIMIT:
                raise ValueError("TRANSFER_LIMIT")
            compressed.update(raw)
            while raw:
                remaining = decoded_limit - report["decoded_bytes"]
                decoded = decoder.decompress(raw, min(CHUNK, remaining + 1))
                if len(decoded) > remaining:
                    report["decoded_overflow_probe_bytes"] = len(decoded) - remaining
                    raise ValueError("DECODED_LIMIT")
                report["decoded_bytes"] += len(decoded)
                expanded.update(decoded)
                target.write(decoded)
                raw = decoder.unconsumed_tail
                if decoder.unused_data:
                    raise ValueError("TRAILING_GZIP_DATA")
        if received != size or not decoder.eof:
            raise ValueError("TRUNCATED_LAYER")
        if "sha256:" + compressed.hexdigest() != digest:
            raise ValueError("LAYER_HASH_MISMATCH")
    return "sha256:" + expanded.hexdigest()


def validate_tar(path):
    """No host extraction. Reject sparse logical expansion and excessive entries."""
    total = entries = 0
    with tarfile.open(path, "r:") as archive:
        for member in archive:
            entries += 1
            total += member.size
            if member.issparse() or entries > 100000 or total > path.stat().st_size:
                raise ValueError("LAYER_ARCHIVE_LIMIT")
            archive.members.clear()
    return entries


def pinned_config():
    with CONFIG.open("rb") as stream:
        raw = stream.read(65537)
    if len(raw) > 65536 or sha(raw) != CONFIG_SHA256:
        raise ValueError("PROPOSAL_PIN_MISMATCH")
    return json.loads(raw)


def acquire(output):
    config = pinned_config()
    output.mkdir(parents=True, exist_ok=False)
    report = {
        "status": "REFUSED",
        "network_bytes": 0,
        "decoded_bytes": 0,
        "requests": 0,
        "redirect_hosts": [],
        "layers": [],
        "dataset_bytes": 0,
    }
    start = time.monotonic()
    previous = signal.getsignal(signal.SIGALRM)

    def timeout(signum, frame):
        raise TimeoutError("ACQUISITION_DEADLINE")

    try:
        if signal.getitimer(signal.ITIMER_REAL)[0]:
            raise ValueError("DEADLINE_ALREADY_ACTIVE")
        signal.signal(signal.SIGALRM, timeout)
        signal.setitimer(signal.ITIMER_REAL, SECONDS)
        report["free_disk_before"] = shutil.disk_usage(output).free
        if report["free_disk_before"] < MIN_FREE + 6 * 1024**3:
            raise ValueError("DISK_HEADROOM")
        report["proposal_sha256"] = CONFIG_SHA256
        report["code_sha256"] = sha(Path(__file__).read_bytes())
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
        _, auth = metadata(opener, AUTH, report)
        token = auth["token"]
        raw_manifest, manifest = metadata(
            opener,
            REGISTRY + "manifests/" + config["manifest_digest"],
            report,
            token,
            config["manifest_digest"],
        )
        expected_layers = [
            {"digest": row["digest"], "bytes": row["size"]} for row in manifest["layers"]
        ]
        if (
            expected_layers != config["layers"]
            or manifest["config"]["digest"] != config["image_config_digest"]
        ):
            raise ValueError("MANIFEST_PROPOSAL_MISMATCH")
        raw_config, image = metadata(
            opener,
            REGISTRY + "blobs/" + config["image_config_digest"],
            report,
            token,
            config["image_config_digest"],
        )
        if (
            image["architecture"] != "arm64"
            or image["os"] != "linux"
            or len(image["rootfs"]["diff_ids"]) != len(expected_layers)
        ):
            raise ValueError("PLATFORM_OR_LAYER_MISMATCH")
        (output / "registry-manifest.json").write_bytes(raw_manifest)
        (output / "image-config.json").write_bytes(raw_config)
        with tarfile.open(output / "r-image.tar", "w", format=tarfile.USTAR_FORMAT) as bundle:
            names = []
            for row, diff in zip(expected_layers, image["rootfs"]["diff_ids"], strict=True):
                if report["network_bytes"] + row["bytes"] + 1 > NETWORK_LIMIT:
                    raise ValueError("TRANSFER_LIMIT")
                path = output / (row["digest"].split(":")[1] + ".tar")
                with response(opener, REGISTRY + "blobs/" + row["digest"], report, token) as stream:
                    if stream.headers.get("Content-Length") not in (None, str(row["bytes"])):
                        raise ValueError("LAYER_SIZE_CHANGED")
                    actual = decode_layer(stream, path, row["digest"], row["bytes"], report)
                if actual != diff:
                    raise ValueError("DIFF_ID_MISMATCH")
                entries = validate_tar(path)
                bundle.add(path, arcname=path.name, recursive=False)
                names.append(path.name)
                report["layers"].append(
                    {
                        **row,
                        "diff_id": actual,
                        "decoded_bytes": path.stat().st_size,
                        "entries": entries,
                    }
                )
                # Exact owned staging file now preserved byte-for-byte in the archive.
                path.unlink()
                print(
                    json.dumps(
                        {"verified_layers": len(names), "decoded_bytes": report["decoded_bytes"]}
                    ),
                    flush=True,
                )
            for name, raw in (
                ("config.json", raw_config),
                (
                    "manifest.json",
                    json.dumps(
                        [{"Config": "config.json", "RepoTags": [], "Layers": names}]
                    ).encode(),
                ),
            ):
                info = tarfile.TarInfo(name)
                info.size = len(raw)
                bundle.addfile(info, io.BytesIO(raw))
        report["archive_bytes"] = (output / "r-image.tar").stat().st_size
        report["import_disk_reservation"] = 3 * report["archive_bytes"] + 256 * 1024**2
        if report["import_disk_reservation"] > 6 * 1024**3:
            raise ValueError("IMPORT_DISK_LIMIT")
        report["image_id"] = config["image_config_digest"]
        report["status"] = "VERIFIED_ARCHIVE_NOT_IMPORTED"
    except Exception as error:
        # Avoid exception text containing bearer/signed URL or arbitrary server output.
        report["error_type"] = type(error).__name__
        report["reason"] = (
            str(error) if isinstance(error, (ValueError, TimeoutError)) else "ACQUISITION_FAILED"
        )
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)
        report["elapsed_seconds"] = time.monotonic() - start
        report["free_disk_after"] = shutil.disk_usage(output).free
        (output / "acquisition.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    resource.setrlimit(resource.RLIMIT_AS, (4 * 1024**3, 4 * 1024**3))
    result = acquire(args.output_dir)
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["status"] == "VERIFIED_ARCHIVE_NOT_IMPORTED" else 1)
