# GNHF OpenRouter research report: E2-M1 runtime/control evidence

Prepared 2026-09-21 (UTC), iteration 1. Research only; no request, install or runtime launch.

## 1. Decision and current blocker

The completed RNA comparison stays INCONCLUSIVE and real paired training stays
incomplete. This pass asks what evidence E2-M1 still needs before a small
controlled HEAD launcher can exist, and the smallest next action.

Decision: **E2-M1 cannot yet support a live HEAD.** The offline capture core and
the read-only preflight exist and pass offline tests, but no hard aggregate
process-tree memory/no-swap control, no external process-tree watchdog, and no
proven non-root Python/TLS runtime are bound to them. Those are technical
evidence gaps, separate from the still-missing owner approval for the one-HEAD
scope. The source contract remains `SOURCE_UNRESOLVED`
(`configs/development_object_source_contract.json:4`); its object-inspection and
network budgets stay zero.

The blocker is a missing *enforceable control binding*, not a missing plan and
not a payload fact. A flag, a mocked test or a sampled RSS value does not prove a
frozen hard ceiling (`tasks/plan.md:73-78`).

## 2. Evidence table

Frozen limits are the pending HEAD contract (`tasks/todo.md:165-167`,
`tasks/plan.md:262-269`, contract lines 42-60). Requirement → source → evidence →
missing proof.

| Requirement | Source and line | Observed evidence | Missing proof |
|---|---|---|---|
| One request, no redirect/retry | `capture_development_head.py:113-121`; `validate_development_head.py:63-64` | RECORDED_PREVIOUSLY: one `conn.request("HEAD",...)`; parser refuses non-200, so a 3xx stops. No retry loop. 45 focused tests (lmstudio REVIEW:43). | Mocked/fake transport only; no live request. Redirect refusal is policy in the parser, not a tested live behavior. |
| 15 s total deadline | `capture_development_head.py:22,65-71` | RECORDED_PREVIOUSLY: one shared monotonic deadline across setup/request/read/parse/cleanup; slow-trickle and slow-cleanup tests (test_development_head_capture.py:379,634). | In-process SIGALRM; Python signals can be delayed by C code (capture docstring:5-6; qwen REVIEW:62). No external watchdog. Mocked clock only. |
| ≤65,536 header bytes | `capture_development_head.py:23,125-136` | RECORDED_PREVIOUSLY: byte-at-a-time `recv(1)` loop capped at 65,536; boundary tests 65536/65537 (test_development_head_capture.py:269,285). | Fake socket; no live observation. TLS/OS buffering excluded by design (capture:5-6). |
| Zero application body/decoded reads | `capture_development_head.py:45,133` | RECORDED_PREVIOUSLY: loop breaks at CRLFCRLF before any body byte; `body_bytes=0` counts application reads. | Semantics only; not TLS/OS-buffer bytes. Needs review for stronger body-byte meaning (plan.md:79-80). |
| 256 MiB aggregate process-tree memory | contract:50; todo.md:185-187 | UNKNOWN for the HEAD launcher. `launcher_head_capture.py:115` sets `runtime_controls=UNVERIFIED`. The R fixture uses container `--memory 4096m` (run_r_fixture.py:54). | No 256 MiB ceiling bound to the Python launcher; no aggregate process-tree measurement; actual peak RSS was not sampled even for the R fixture (r_reader REVIEW:86). |
| Zero swap | contract:51; run_r_fixture.py:55 | RECORDED_PREVIOUSLY: R fixture sets `--memory-swap == --memory` (no swap) and verifies it (run_r_fixture.py:90-116). | Not bound to the HEAD launcher; host cgroup swap state UNKNOWN now. |
| ≤1 MiB retained output | contract:49 | UNKNOWN. Capture caps the header record; preflight never reserves an output dir (`launcher_head_capture.py:116`). | No output-size cap or output reservation in any bound launcher. |
| ≥10 GiB free host disk | `launcher_head_capture.py:39,166-168` | OBSERVED_NOW: `df -k .` reports 19,400,496 KiB ≈ 18.5 GiB free, above the 10 GiB floor. Implemented and tested (test_launcher_head_capture.py:258). | Race-free reservation; free space is falling versus recorded 22.5–27.75 GiB. |
| Non-root isolation | run_r_fixture.py:52,107 | RECORDED_PREVIOUSLY: R fixture runs `--user 65534:65534`, read-only rootfs, no network/mounts; verified before start. | Not bound to the HEAD launcher; no proven non-root Python/TLS container. |
| Python/TLS runtime identity | contract:54; todo.md:185-187 | UNKNOWN. No `.venv-p22` in this worktree; `python3.11` exists on PATH; docker binary present (`/usr/local/bin/docker`). | Compatible pinned Python/TLS identity not established; runtime availability not probed by instruction. |
| Process-tree watchdog | plan.md:73-78; qwen REVIEW:62 | UNKNOWN. Only in-process SIGALRM exists. | No external watchdog covering startup/connect/TLS/read/cleanup with one wall budget. |
| Non-root/no-host-data-mount config | todo.md:190-191 | RECORDED_PREVIOUSLY: pattern proven for the R fixture only. | Not bound to the HEAD launcher. |

All four launcher pins match now: contract SHA-256 `9a13d8be…` and source note
`66b1d815…` (both required), plus capture `335d35c5…` and validator `c7614892…`
(`launcher_head_capture.py:16-37`). The three supporting REVIEW.md records are
absent from this worktree (ignored); they were read from the original checkout
without edits.

## 3. Proposed bounded offline tests and necessary controls

All items are PROPOSED; none is written or run in this pass.

1. **Hard memory/no-swap binding.** Reuse the R-fixture pattern
   (`run_r_fixture.py:34-73,90-116`): create one owned container at
   `--memory 256m --memory-swap 256m --pids-limit N --user 65534:65534
   --network none --read-only`, inspect limits before start, and run a
   hostile child tree. Expected: container refuses/`OOMKilled` at the aggregate
   ceiling, swap stays zero, and no descendant survives. Permission: authorization
   to launch one UUID-owned local container (the local-resource approval is
   historical and scoped to the R reader). Refusal: nonzero swap or unenforceable
   limit must refuse before the workload.
2. **External process-tree watchdog.** Start a non-cooperative child tree that
   ignores SIGTERM; require an external killer to terminate the whole tree within
   one wall budget and prove `Running=false, Pid=0`. Expected output: bounded
   cleanup record. Permission: same one-container allocation.
3. **Output cap and reservation.** Offline unit tests only: bound serialized
   output to 1 MiB, reserve the destination before any request, and refuse reuse.
   Entry point `launcher_head_capture.py`/new launcher test. No permission needed.
4. **Runtime/TLS identity pin.** Read-only inventory of the intended Python
   image, OpenSSL version and trust store, with the runtime identity hashed into
   the preflight record. Permission: read-only container inspection.
5. **Redirect/non-200/length offline cases.** Already largely covered by
   `tests/test_development_head_capture.py` and `tests/test_development_head.py`;
   extend only for the launcher binding. No new permission.

## 4. One next action, acceptance criteria, stop condition

**Next action:** E2-M1b, a ≤30-minute offline native-control design that reuses
`run_r_fixture.py:create_args/verify_container` to define the exact single-container
probe allocation for the HEAD launcher (256 MiB aggregate memory, zero swap,
non-root, no network/mounts, external watchdog, 1 MiB output), and records the
runtime/TLS identity and current host snapshot.

- **Entry points:** `run_r_fixture.py:34-116` (control pattern),
  `launcher_head_capture.py` (preflight to extend), `capture_development_head.py`
  (core to wrap).
- **Expected output:** one small ignored `runtime_controls.json` mapping each
  frozen limit to an inspected enforcement mechanism or an explicit unknown.
- **Acceptance criteria:** every limit in section 2 is either bound to a named,
  inspected control or labeled UNKNOWN with a reason; no network request; no
  scientific gate changes.
- **Stop condition:** any limit that cannot be enforced, or a missing/uninspectable
  runtime, stops with a scoped blocker; no install, no live HEAD, no retry.

## 5. Self-review

- **Strongest objection:** the report may be read as new runtime evidence. It is
  not; the only OBSERVED_NOW facts are date/OS/arch/disk and file-path existence.
  Every control claim is RECORDED_PREVIOUSLY or UNKNOWN.
- **Unresolved conflicts:** plan.md:262-269 still labels the next live step HEAD,
  while todo.md:165-167 and the contract match; the superseded September 12
  listing-GET proposal (r_reader REVIEW:11-13) must not be revived.
- **Unexamined evidence:** whether the pinned R image
  `sha256:264df259…` and a compatible non-root Python image remain cached is
  UNKNOWN (Docker socket not contacted). Actual `.rda`/Seurat/ChromatinAssay
  support and all scientific gates remain open and untouched.
