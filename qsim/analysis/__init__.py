"""Series→statistic→verdict layer for the field battery (analysis-tooling
design §1). Consumes qsim.observe views and header.json; NEVER parses
events.jsonl itself. Stdlib-only; series arithmetic lives in numerics.py
(the numpy-swap seam)."""
