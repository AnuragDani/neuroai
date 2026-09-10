# Local-worker pilot: F4 rejected

Decision: local inference works, but this worker has not passed the scientific
configuration checkpoint. F4 remains incomplete. F5 was not started. No real
analysis, paired training, new dataset downloads, paid compute, push or merge occurred.

## Scope and provenance

- Base: `9d3525e`; isolated branch `codex/p22-local-rna` in
  `/private/tmp/p22-local-rna.ILXNT6/workspace`.
- Implementation worker: installed Ollama `qwen3-coder-next:latest`, explicitly
  routed to `http://127.0.0.1:11434/v1/`. Codex CLI supplied the worker tools.
- Supervisor: current Codex model, plus independent read-only review. Supervisor
  supplied verified evidence after local metadata-reading failures; did not
  replace the worker with cloud implementation.
- Worker output SHA256:
  `deaf5427f0ac5abf12c9a80dca98404fc77a97f28e9d38077089586c3d0b3ab3`.
  This is a REJECTED draft, not an executable or approved scientific protocol.
- Original checkout's 12 dirty/untracked files were fingerprinted and all
  fingerprints matched after the attempt. Existing RNA outputs were not changed.

## Runtime outcome

The original error came from inherited `model_reasoning_effort="medium"` on a
model whose local catalog advertises no thinking support. Session-only overrides
`model_reasoning_effort="none"` and `model_reasoning_summary="none"` enabled local
inference. Global configuration was not edited by the supervisor.

The initial worker invented MCP file servers. One stripped-config retry also
discarded the selected provider profile and was rejected by the ChatGPT endpoint
before inference; no cloud implementation ran. The subsequent launcher explicitly
pinned the loopback provider, disabled apps/plugins and retained workspace-write
sandboxing. No rules or sandbox bypass was used. The worker then performed local
file/hash reads, but repeatedly mishandled categorical H5AD metadata. One final,
evidence-guided attempt produced the draft. No further retries were launched.

The final config-generation attempt reported 193,852 input tokens (176,727 cached),
4,662 output tokens and zero reasoning tokens. These are local inference counts,
NOT the total pilot cost; interrupted attempts and cloud supervision are excluded.

## Independent review: reject

1. Draft line 102 sets `exclude_chr21=false`, changing the frozen gene universe.
2. Line 79 specifies `raw_counts ~ DS + PCW + female`, rather than fitting
   `log1p(CPM)`. Line 109's `post_gene_filtering=true` is also ambiguous against
   the required all-raw-gene denominator; no normalization was actually run.
3. Gene rules omit the existing expression floor: at least 1 CPM in at least
   half of EACH class, reapplied after every donor omission.
4. Boolean delta flags do not define Gi, the two delta formulas, newly eligible
   gene exclusion, or absolute within-comparison ranking. Shared-donor/shared-cell
   non-independence is not disclosed.
5. Numeric tolerances lack explicit mismatch refusal and exact identity/count/
   order checks. Constant-vector, insufficient-class and rank-failure handling
   are not frozen.

Input hashes, comparison mappings, baseline numbers and ordered donor IDs match
the inspected reference. Valid JSON does not close the scientific checkpoint.

## Verification actually performed

- Existing `make lint`: passed; 101 files already formatted.
- Existing `make test-fast`: 576 passed, 32 deselected, 79.72 seconds.
  These are baseline tests, NOT tests of a new diagnostic implementation.
- Worker verified H5AD, workbook and reference CSV SHA256 values.
- Main independently read the completed draft and canonical estimator; a separate
  reviewer independently rejected the same contract gaps.
- Three direct contract checks rejected chromosome-21 inclusion, raw-count
  response and ambiguous post-filter normalization. Expected assertion failure;
  not a successful new-feature test.
- All 12 original dirty-file SHA256 checks passed after the attempt.
- F5 fixture tests, baseline reproduction, omissions and result generation:
  NOT RUN. No F4/F5 checkbox was marked complete.

## Smallest next action

Repair and review F4 before any F5 code or real analysis. Use small, explicitly
scoped patches with executable contract checks; this pilot does not justify
unattended end-to-end work by this local model. A supervisor-led implementation
with local assistance would be a different execution arrangement, not a silent
fallback. No larger GPU is indicated by these tool-use and protocol errors.

For a later real run, macOS `RLIMIT_AS` aliases `RLIMIT_RSS`; neither proves a hard
6 GiB allocation ceiling here. Existing resource helpers only measure after a
stage. Review timeout/RSS monitoring honestly before execution; do not claim
sampled monitoring is a never-exceed memory guarantee.
