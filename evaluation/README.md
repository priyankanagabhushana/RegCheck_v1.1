# Evaluation Scope

RegCheck v1.1 contains two complementary evaluation paths.

## Contract-level evaluation

`load_known_deviations()` uses scenario-specific synthetic contracts. This is
useful for checking whether graph differencing and deterministic constraints
respond to controlled changes, but it does not measure PDF parsing, LLM
extraction, or end-to-end document accuracy.

The COMPARE path reconstructs contracts from published aggregate annotations.
It evaluates the constraint and graph layers against those annotations; it is
not a substitute for running the original registration and paper documents
through the complete extraction pipeline.

## Stronger end-to-end evaluation

An end-to-end case should provide the original registration and publication
files, parser metadata, human evidence spans, dimension-level judgements, and
adjudication notes. Results should report extraction, matching, and judgement
metrics separately so an error in one stage is not attributed to the whole
system.
