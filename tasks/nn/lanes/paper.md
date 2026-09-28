# paper lane

- 2026-09-28 N33 (finish-base): Vault `paper-nn/` allow-list copy (draft, fig1–fig5, refs, claims, self_review); sha256 match; replaced buggy-lane vault draft; MOM/packet untouched; header `DRAFT_V1_PARTIAL:N34`. Next: N34 final verification.
- 2026-09-28 N32 (finish-base): Wrote `paper/self_review.md` (8 objections); age confound Limitations add; 7/8 cite existing sections; header `DRAFT_V1_PARTIAL:N33-N34`. Next: N33 vault copy.
- 2026-09-28 N31 (finish-base): Formal `check_paper.py` gate 5/5 PASS (citations/numbers/forbidden/figures/word_counts; 0 failures; `--json` ok=true); no draft repairs; header `DRAFT_V1_PARTIAL:N32-N34`. Next: N32 adversarial self-review.
- 2026-09-28 N30 (finish-base): Rewrote title + Abstract under F4 from framing.md/claims.csv (152≤200w; B_NULL −0.0067; replaced stale “ladder never ran”); `check_paper.py` 5/5 PASS; header `DRAFT_V1_PARTIAL:N31-N34`. Next: N31 formal checker + N32 self-review.
- 2026-09-28 N29 (finish-base): Rewrote Discussion+Limitations under F4 (506≤700w; mandatory limits + PC N/A + chr21 DEFERRED); `check_paper.py` 5/5 PASS; header `DRAFT_V1_PARTIAL:N30-N34`. Abstract/title still stale. Next: N30 Abstract + title.
- 2026-09-28 N27 (finish-base): Rewrote Results from accepted ladder_v2 JSON + `paper/claims.csv`; `check_paper.py` 5/5 PASS; header `DRAFT_V1_PARTIAL:N29-N34`. Abstract/Discussion/Limitations still stale. Next: N29 Discussion + Limitations.
- 2026-09-28 N25 (finish-base): built fig1–fig5 from accepted planted/ladder_summary/faithfulness/spectrum JSON via `paper/make_figures.py --only all`; removed stale fig1_architecture and buggy fig4_spectrum; SKIPPED=[]. Next: N27 Results + claims.csv.
- Prior agy lane N24–N34 used blocked/buggy evidence and is superseded for framing/Results; keep Methods/Intro/Related Work from N26/N28 unless facts change.
