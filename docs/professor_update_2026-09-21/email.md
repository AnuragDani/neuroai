Subject: P22 update: corrected paired inputs, rerun internal comparison, and remaining limits

Hi Professor Fang,

This is an unsent draft for your review. It reports only internal work; nothing
here has been sent, published, or shared.

Since the last update I reproduced and repaired two measurement defects in the
paired RNA+ATAC inputs and reran the internal comparison on the corrected inputs.

- RNA input: the loader was consuming the processed H5AD `X` block while calling
  it raw counts. It now consumes the integer `raw/X` block with the `raw/var` gene
  axis, and refuses non-integer or negative values.
- ATAC input: the overlap unit was summing column five (supporting read pairs
  including duplicates), which overcounts. The unit is now one count per unique
  qualifying fragment record, and the BGZF/tabix reader was repaired and checked
  against HTSlib on local and real remote regions.

The corrected internal comparison is again a null: cross-attention minus matched
token-concatenation donor balanced accuracy is +0.0067 with a 95% donor-bootstrap
interval of [-0.025, +0.035], below the frozen 0.07 practical margin. The old
+0.0333 estimate was measured on the defective inputs and is preserved only as
exploratory history. Faithfulness interventions still show the models depend
mostly on the RNA view, and the null holds across initialization seeds.

This is a corrected internal result, not biological validation. Two limits remain:
the retained 256-region feature rule is still chromosome-1 biased (163-219 of 256
regions per fold), and external paired evaluation is still blocked by access and
transport problems with no established common measurement space. I am not asking
to relax any access control. The completed separate RNA replication also remains
inconclusive.

Please start with `one_pager.md`. The canonical notebook now exposes the corrected
workflow and a safe-mode executed copy is included.

Best,
Anurag
