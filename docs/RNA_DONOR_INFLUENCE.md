# RNA donor-influence diagnostic

This is the F4–F5 post-hoc diagnostic, not a replacement for the completed RNA
replication study. It does not complete paired-input feasibility or neural training.
The original four comparisons and headline remain inconclusive; G8 is unchanged.

## Reviewed contract

`configs/rna_donor_influence.json` pins the three local inputs, original estimator
source hashes, donor order, four comparisons, normalization, gene filters and
baseline counts/correlations. Its canonical JSON SHA256 is
`d51a69cc997fe3a80615ea76bdf9d9504a5334c05fe09eb8fe77a623d266cf58`.
Any changed contract or source hash refuses execution. No runtime override can
weaken the contract. A future change requires a separately reviewed protocol.

The command first reproduces every baseline (rho tolerance 1e-10, no relative
tolerance; exact donor/count checks), then omits every donor. Counts are streamed
once per unique population. Existing full-gene library totals and log1p(CPM)
normalization are retained. The expression floor is reapplied per omission.

For Gi, the intersection of baseline and omission-eligible genes, it reports:

- same-support delta: rho_loo(Gi) minus rho_baseline(Gi);
- support delta: rho_baseline(Gi) minus rho_baseline(G0);
- lost/new gene counts, identities, Gi hash, class support and fit status.

New genes do not enter the endpoint. Invalid fits stay unavailable; covariates
and scientific gates are never relaxed. All comparisons share discovery donors;
the two RG comparisons also share discovery cells. Influence is descriptive,
not causal, independent replication, a power test or external-donor uncertainty.

## Run from an isolated checkout

Keep the pinned H5AD, workbook and original reference CSV at their config paths.
Use the existing environment without reinstalling dependencies. When sharing an
environment installed editable in another checkout, `PYTHONPATH=src` is required.
Choose a new output directory; existing directories refuse execution.

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src make lint
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src make test-fast
P22_PROFESSOR_APPROVED=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src \
  .venv-p22/bin/python scripts/diagnose_rna_replication.py \
  --output-dir reports/generated/rna_donor_influence_NEW_RUN
```

The last command uses the existing per-run attestation, not a new approval.
The supervisor owns one CPU child, limits wall time to 1,800 seconds and samples
its RSS every 0.1 seconds. It stops at 5 GiB, leaving headroom under the 6 GiB
budget. OS query latency and short peaks remain possible: this is not a kernel
hard memory ceiling. Missing monitoring refuses launch or stops the owned child.
No downloads, cache, permutations, bootstraps, paid compute or GPU work occur.

## Verify completion

Require both `run.json` and `resources.json` to say `COMPLETED`. A partial folder
or plot is not a completed run. Check the artifact SHA256 values, all four baseline
records, 68 unique real donor/comparison rows and before/after input hashes.
`baseline_genes.csv` fingerprints G0 derived now; the old run did not save gene IDs.
The command writes only new output artifacts, never original validation rows.
Preserve dirty-file and notebook hashes independently before and after execution.

The earlier local-only pilot remains rejected, documented in
`LOCAL_WORKER_PILOT_2026-09-10.md`. This implementation is supervisor-led following
explicit user approval. A small local-model test draft required supervisor
correction; passing local inference was not treated as scientific verification.
