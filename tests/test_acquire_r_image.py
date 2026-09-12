"""Offline abuse cases for the single pinned runtime acquisition."""

import gzip
import hashlib
import importlib.util
import io
import json
import tarfile
from pathlib import Path
from types import SimpleNamespace

import pytest


def module():
    spec = importlib.util.spec_from_file_location(
        "acquire_r_image", Path(__file__).parents[1] / "scripts/acquire_r_image.py"
    )
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


@pytest.mark.parametrize("failure", [None, "hash", "truncated", "trailing", "limit", "size"])
def test_layer_stream_is_bounded_and_verified(tmp_path, failure):
    reader = module()
    decoded = b"sparse fixture" * 1000
    raw = gzip.compress(decoded, mtime=0)
    expected = "sha256:" + hashlib.sha256(raw).hexdigest()
    size = len(raw)
    if failure == "hash":
        expected = "sha256:" + "0" * 64
    elif failure == "truncated":
        raw = raw[:-2]
        size = len(raw)
    elif failure == "trailing":
        raw += b"extra"
        size = len(raw)
    elif failure == "size":
        size -= 1
    report = {"network_bytes": 0, "decoded_bytes": 0}
    args = (io.BytesIO(raw), tmp_path / "layer", expected, size, report)
    if failure:
        with pytest.raises(ValueError):
            reader.decode_layer(*args, decoded_limit=100 if failure == "limit" else 20000)
    else:
        diff = reader.decode_layer(*args, decoded_limit=20000)
        assert diff == "sha256:" + hashlib.sha256(decoded).hexdigest()
        assert (tmp_path / "layer").read_bytes() == decoded
        assert report == {"network_bytes": len(raw), "decoded_bytes": len(decoded)}
    assert report["network_bytes"] <= size + 1
    assert report["decoded_bytes"] <= (100 if failure == "limit" else 20000)


def test_output_reuse_and_redirect_credentials_refused(tmp_path):
    reader = module()
    with pytest.raises(FileExistsError):
        reader.acquire(tmp_path)
    for url in (
        "http://production.cloudflare.docker.com/x",
        "https://evil.test/x",
        "https://user@production.cloudflare.docker.com/x",
    ):
        with pytest.raises(ValueError):
            reader.check_redirect(url)
    reader.check_redirect("https://production.cloudflare.docker.com/x?opaque=signed")


def test_changed_proposal_refuses_before_output_or_network(tmp_path, monkeypatch):
    reader = module()
    changed = tmp_path / "proposal.json"
    changed.write_text(reader.CONFIG.read_text().replace("4.6.1", "4.6.2"))
    monkeypatch.setattr(reader, "CONFIG", changed)
    monkeypatch.setattr(reader.urllib.request, "build_opener", lambda *args: pytest.fail("network"))
    with pytest.raises(ValueError, match="PROPOSAL_PIN_MISMATCH"):
        reader.acquire(tmp_path / "output")
    assert not (tmp_path / "output").exists()


@pytest.mark.parametrize("failure", [None, "manifest", "config", "diff"])
def test_fake_registry_archive_end_to_end(tmp_path, monkeypatch, failure):
    reader = module()
    layer = io.BytesIO()
    with tarfile.open(fileobj=layer, mode="w") as archive:
        member = tarfile.TarInfo("fixture.txt")
        member.size = 2
        archive.addfile(member, io.BytesIO(b"ok"))
    decoded = layer.getvalue()
    raw = gzip.compress(decoded, mtime=0)
    layer_digest = reader.sha(raw)
    config = json.dumps(
        {
            "architecture": "arm64",
            "os": "linux",
            "rootfs": {
                "diff_ids": [reader.sha(decoded) if failure != "diff" else reader.sha(b"wrong")]
            },
        }
    ).encode()
    manifest = json.dumps(
        {
            "layers": [{"digest": layer_digest, "size": len(raw)}],
            "config": {"digest": reader.sha(config)},
        }
    ).encode()
    proposal = {
        "layers": [{"digest": layer_digest, "bytes": len(raw)}],
        "manifest_digest": reader.sha(manifest),
        "image_config_digest": reader.sha(config),
    }
    config_path = tmp_path / "proposal.json"
    config_path.write_text(json.dumps(proposal))
    monkeypatch.setattr(reader, "CONFIG", config_path)
    monkeypatch.setattr(reader, "CONFIG_SHA256", reader.sha(config_path.read_bytes()))
    monkeypatch.setattr(reader.shutil, "disk_usage", lambda _: SimpleNamespace(free=100 * 1024**3))
    responses = {
        reader.AUTH: b'{"token":"unit-test-token"}',
        reader.REGISTRY + "manifests/" + reader.sha(manifest): manifest,
        reader.REGISTRY + "blobs/" + reader.sha(config): config,
        reader.REGISTRY + "blobs/" + layer_digest: raw,
    }
    if failure in ("manifest", "config"):
        kind = "manifests/" if failure == "manifest" else "blobs/"
        original = manifest if failure == "manifest" else config
        responses[reader.REGISTRY + kind + reader.sha(original)] = b"{}"

    def open_response(request, timeout):
        stream = io.BytesIO(responses[request.full_url])
        stream.status = 200
        stream.headers = {}
        return stream

    monkeypatch.setattr(
        reader.urllib.request, "build_opener", lambda *args: SimpleNamespace(open=open_response)
    )
    result = reader.acquire(tmp_path / "output")
    assert result["status"] == ("REFUSED" if failure else "VERIFIED_ARCHIVE_NOT_IMPORTED")
    assert result["dataset_bytes"] == 0
    assert "unit-test-token" not in json.dumps(result)
    if not failure:
        with tarfile.open(tmp_path / "output/r-image.tar") as archive:
            assert archive.extractfile(layer_digest.split(":")[1] + ".tar").read() == decoded
