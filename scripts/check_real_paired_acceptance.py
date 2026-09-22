"""Inspect the shared real-paired acceptance decision for the current artifacts.

This is the executable evidence path for the acceptance gate. It loads the real
development inputs, builds the evidence bundle from the artifacts actually
consumed, and evaluates it against the prospective requirements plus an optional
measured manifest. It never trains, never reaches the network, and never promotes
a claim: a refused decision is the expected outcome for the historical inputs and
for any run without a measured manifest.

Replay::

    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:scripts \
      <python> scripts/check_real_paired_acceptance.py \
      --out reports/generated/acceptance_binding_20260921/decision.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _path in (ROOT / "src", ROOT / "scripts"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from p22.eval.multiome_protocol import MultiomeProtocol  # noqa: E402
from run_real_paired_comparison import _acceptance_decision, _fold_map  # noqa: E402
from run_real_paired_pilot import DEFAULT_H5AD, load_development_inputs  # noqa: E402

DEFAULT_ATAC = ROOT / "reports/generated/repeated_comparison_20260921/counts/counts.npz"
DEFAULT_REGIONS = ROOT / "reports/generated/repeated_comparison_20260921/region_sets.json"
DEFAULT_REQUIREMENTS = ROOT / "configs/real_paired_acceptance_2026-09-21.json"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "configs/paired_multiome.json")
    parser.add_argument("--h5ad", default=DEFAULT_H5AD)
    parser.add_argument("--atac-matrix", default=str(DEFAULT_ATAC))
    parser.add_argument("--region-sets", default=str(DEFAULT_REGIONS))
    parser.add_argument("--requirements", type=Path, default=DEFAULT_REQUIREMENTS)
    parser.add_argument("--manifest", type=Path, default=None)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)

    protocol = MultiomeProtocol(**json.loads(args.config.read_text())["protocol"])
    views, metadata, fingerprints = load_development_inputs(
        args.h5ad, args.atac_matrix, protocol
    )
    del views
    region_sets = json.loads(Path(args.region_sets).read_text())
    folds = list(_fold_map(metadata, protocol).values())
    decision = _acceptance_decision(
        protocol,
        fingerprints,
        region_sets,
        folds,
        metadata,
        args.atac_matrix,
        args.region_sets,
        args.requirements,
        args.manifest,
    )
    payload = {
        "record_type": "real_paired_acceptance_decision",
        "atac_matrix": str(args.atac_matrix),
        "region_sets": str(args.region_sets),
        "requirements": str(args.requirements),
        "manifest": str(args.manifest) if args.manifest else None,
        "decision": decision.to_dict(),
    }
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(json.dumps(payload["decision"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
