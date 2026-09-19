"""Offline source-resolution fixtures; no public request in tests."""

import gzip
import hashlib
import io
import json
import subprocess
import sys
import tarfile
import time

import pytest
from scripts import resolve_nemo_source as source


def bag(*, fetch=None, checksums=None, extra=None):
    path = "data/" + source.TARGET["filename"]
    members = {
        "release/fetch.txt": fetch
        or f"https://example.org/counts {source.TARGET['bytes']} {path}\n",
        "release/manifest-md5.txt": checksums or f"{source.TARGET['md5']} {path}\n",
    }
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode="w") as archive:
        for name, value in members.items():
            member = tarfile.TarInfo(name)
            raw = value.encode()
            member.size = len(raw)
            archive.addfile(member, io.BytesIO(raw))
        if extra:
            member = tarfile.TarInfo(extra)
            if extra == "link":
                member.type = tarfile.SYMTYPE
                member.linkname = "release/fetch.txt"
            archive.addfile(member)
    return gzip.compress(stream.getvalue(), mtime=0)


def pin(monkeypatch, raw):
    monkeypatch.setattr(source, "BAG_BYTES", len(raw))
    monkeypatch.setattr(source, "BAG_SHA256", hashlib.sha256(raw).hexdigest())


class Response(io.BytesIO):
    status = 200

    def __init__(self, raw, headers=None):
        super().__init__(raw)
        self.headers = headers or {}


class Opener:
    def __init__(self, response):
        self.response = response
        self.requests = []

    def open(self, request, **kwargs):
        self.requests.append(request)
        return self.response


@pytest.fixture
def evidence(tmp_path, monkeypatch):
    path = tmp_path / "evidence.md"
    path.write_text("fixture evidence")
    monkeypatch.setattr(source, "EVIDENCE_PATH", path)
    monkeypatch.setattr(source, "EVIDENCE_SHA256", hashlib.sha256(path.read_bytes()).hexdigest())


def test_resolves_two_manifests_and_saves_replayable_bag(tmp_path, monkeypatch, evidence):
    raw = bag()
    pin(monkeypatch, raw)
    opener = Opener(Response(raw, {"ETag": '"bag-version"'}))
    output = tmp_path / "out"
    result = source.resolve(output, opener=opener)
    assert result["stop_reason"] == "RESOLVED"
    assert result["resolved_payload"]["url"] == "https://example.org/counts"
    assert result["resolved_payload"]["md5"] == source.TARGET["md5"]
    assert result["body_bytes"] == len(raw)
    assert result["decoded_bytes"] > len(gzip.decompress(raw))
    assert len(opener.requests) == 1
    assert opener.requests[0].get_method() == "GET"
    assert opener.requests[0].full_url == source.BAG_URL
    assert result["headers"]["ETag"] == '"bag-version"'
    assert (output / "source-bag.tgz").read_bytes() == raw
    assert json.loads((output / "source_identity.json").read_text()) == result
    assert not (output / "release").exists()
    with pytest.raises(FileExistsError):
        source.resolve(output, opener=opener)
    assert len(opener.requests) == 1


@pytest.mark.parametrize(
    "case",
    [
        "hash",
        "length",
        "size",
        "md5",
        "duplicate",
        "path",
        "unsafe",
        "link",
        "truncated",
        "expanded",
    ],
)
def test_invalid_bags_never_resolve(tmp_path, monkeypatch, evidence, case):
    raw = bag()
    if case == "size":
        raw = bag(fetch=f"https://example.org/counts 1 data/{source.TARGET['filename']}\n")
    elif case == "md5":
        raw = bag(checksums=f"{'0' * 32} data/{source.TARGET['filename']}\n")
    elif case == "duplicate":
        row = (
            f"https://example.org/counts {source.TARGET['bytes']} "
            f"data/{source.TARGET['filename']}\n"
        )
        raw = bag(fetch=row * 2)
    elif case == "path":
        raw = bag(checksums=f"{source.TARGET['md5']} other/{source.TARGET['filename']}\n")
    elif case in ("unsafe", "link"):
        raw = bag(extra="../escape" if case == "unsafe" else "link")
    elif case == "truncated":
        raw = raw[:-5]
    pin(monkeypatch, raw)
    if case == "hash":
        monkeypatch.setattr(source, "BAG_SHA256", "0" * 64)
    elif case == "length":
        monkeypatch.setattr(source, "BAG_BYTES", len(raw) + 1)
    elif case == "expanded":
        monkeypatch.setattr(source, "MAX_DECODED", 100)
    opener = Opener(Response(raw))
    result = source.resolve(tmp_path / "out", opener=opener)
    assert result["stop_reason"] != "RESOLVED"
    assert result["resolved_payload"] is None
    assert len(opener.requests) == 1
    assert result["decoded_bytes"] <= source.MAX_DECODED
    if case not in ("hash", "length"):
        assert (tmp_path / "out/source-bag.tgz").read_bytes() == raw


@pytest.mark.parametrize("case", ["redirect", "encoding", "body_cap", "slow", "stall", "dns"])
def test_transport_refusals_are_bounded(tmp_path, monkeypatch, evidence, case):
    raw = bag()
    pin(monkeypatch, raw)
    response = Response(raw)
    if case == "redirect":
        response.status = 302
    elif case == "encoding":
        response.headers = {"Content-Encoding": "gzip"}
    elif case == "body_cap":
        monkeypatch.setattr(source, "MAX_BODY", 10)
    elif case in ("slow", "stall"):
        monkeypatch.setattr(source, "NETWORK_SECONDS", 0.08)

        def delayed_read(count):
            time.sleep(0.02 if case == "slow" else 0.5)
            return b"x"

        response.read1 = delayed_read
    opener = Opener(response)
    if case == "dns":
        monkeypatch.setattr(source, "NETWORK_SECONDS", 0.08)

        def blocked_open(request, **kwargs):
            opener.requests.append(request)
            time.sleep(0.5)
            return response

        opener.open = blocked_open
    start = time.monotonic()
    result = source.resolve(tmp_path / "out", opener=opener)
    assert result["stop_reason"] != "RESOLVED"
    assert result["resolved_payload"] is None
    assert result["body_bytes"] <= source.MAX_BODY
    assert len(opener.requests) == 1
    if case in ("slow", "stall", "dns"):
        assert result["stop_reason"] == "NETWORK_DEADLINE"
        assert time.monotonic() - start < 0.4
    if case in ("redirect", "encoding"):
        assert result["body_bytes"] == 0


def test_missing_evidence_is_zero_request(tmp_path, monkeypatch):
    monkeypatch.setattr(source, "EVIDENCE_PATH", tmp_path / "missing")
    opener = Opener(Response(b""))
    result = source.resolve(tmp_path / "out", opener=opener)
    assert result["stop_reason"] == "SOURCE_IDENTITY_UNRESOLVED"
    assert result["request_attempted"] is False
    assert result["requests"] == []
    assert result["body_bytes"] == result["decoded_bytes"] == 0
    assert result["resolved_payload"] is None
    assert not opener.requests


def test_production_redirect_handler_never_follows():
    assert (
        source.NoRedirect().redirect_request(None, None, 302, "move", {}, "https://example.org")
        is None
    )


def test_fresh_process_preserves_frozen_production_contract(monkeypatch):
    monkeypatch.setattr(source, "BAG_URL", "https://fixture.invalid")
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import json; from scripts import resolve_nemo_source as s; "
            "print(json.dumps([s.BAG_URL,s.BAG_BYTES,s.BAG_SHA256,s.MAX_BODY,"
            "s.MAX_DECODED,s.NETWORK_SECONDS,s.TARGET]))",
        ],
        capture_output=True,
        text=True,
        check=True,
        timeout=10,
    )
    frozen = json.loads(result.stdout)
    assert frozen[0] == (
        "https://data.nemoarchive.org/publication_release/"
        "Vuong_delaTorre_Human_snMultiome-2026-05-04/"
        "Analysis_bag_3_Vuong_delaTorre_Human_snMultiome_Analysis_ATAC_Open.tgz"
    )
    assert frozen[1:6] == [
        1867,
        "4698c4b80d1e1bde7588b9b0979beb113df2ca24aebf54afbbac606eaf064d45",
        65536,
        262144,
        15,
    ]
    assert frozen[6] == {
        "filename": "VuongWeber_2025_DSdevctx_atac_counts_20260128.mex.tar.gz",
        "bytes": 1540753269,
        "md5": "796c8b3aa587b257af0a46615a437dba",
    }
    invalid = subprocess.run(
        [sys.executable, "scripts/resolve_nemo_source.py", "--url", "https://fixture.invalid"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert invalid.returncode == 2
