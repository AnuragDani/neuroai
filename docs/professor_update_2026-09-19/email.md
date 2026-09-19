Subject: P22 update: completed RNA comparison and paired-data next step

Hi Professor Fang,

I completed the planned external RNA effect comparison and packaged the code,
executed notebooks, and readable HTML outputs with a one-page summary.

All four prespecified comparisons were inconclusive: their correlation intervals
crossed zero. The discovery analysis used 9 Down syndrome and 8 control donors;
the external comparison used published effect summaries from 5 Down syndrome
and 5 control donors. The local and free-CPU Colab results matched exactly.
This establishes computational reproducibility, not biological replication.

I also completed a post-hoc donor-influence analysis with 68 omissions. One donor
had the largest influence across the comparisons. I kept all donors and did not
change the primary conclusion or select exclusions to improve agreement.

The paired RNA+ATAC model code is in place, including donor-aware evaluation and
cross-attention controls, but real paired training has not run. The remaining
problem is input acceptance: the two inspected raw libraries have no exactly
shared peak intervals, and processed-object compatibility and quality-control
semantics remain unresolved. The processed objects are not yet proven unusable.

My proposed next step is the bounded runtime review needed for a safe inspection
of those objects. If the inputs pass the existing criteria, I can then freeze
the real-data comparison and move to training. I am not proposing a larger GPU
purchase or a full fragment download at this stage.

Please start with `one_pager.md` and the two HTML files linked there. They show
the completed RNA result and the narrower scope of the latest Colab software
run without a Python installation. The full notebook index separates current
evidence from historical snapshots.

Best,
Anurag
