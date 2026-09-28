# Future work (not run in this assignment)

Recorded under decision-tree G9: do not start new experiments here.

1. **External validation cohort** — required before any generalization claim beyond the
   internal 30-donor development set (`STUDY_PARTIAL` remains).
2. **Planted PC for pairing** — save/refit S4/S5 δ=1.0 models under accepted widths so
   N13 I3 pairing tags can be sensitivity-checked (currently PC `N/A`).
3. **Chr21-excluded cell-score export** — optional N15 follow-on; would enable a direct
   spectrum dosage-alignment table (currently `NOT_NEEDED` via per-cell dosage column).
4. **Regulatory / functional ATAC panel** — current tie-break and gene-activity panels are
   measurement panels, not regulatory maps.
5. **Larger donor n** — spectrum and CA−TC CIs are wide at n=30; power, not protocol
   change, is the binding constraint for detecting small advantages.
