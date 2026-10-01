# Local acceptance evidence

Measured on 2026-10-01 on this Windows machine, Python 3.12.10, CPU only.

Offline editable installation completed with no dependencies or network access.
The installed sor.exe ran fixtures, run, and report as three separate processes.
Combined end-to-end elapsed wall time: 0.932236 seconds (measured locally).
Acceptance threshold: under 5 seconds. Result: PASS.

Synthetic fixture counts matched the independent hand-computed expectations exactly:
200 records = 25 unchanged + 100 repaired + 75 rejected; 200 labelled,
200 correct, 0 false positives, 0 false negatives. These are synthetic results.
The Markdown report includes provenance and per-record source, output and edit traces.

pytest: 53 passed. Tests include a five-record hand-written synthetic demo,
empty input, malformed envelopes, unsupported formats, schema drift, duplicate ids,
negative amounts, future dates, duplicate keys, nonfinite values, unsafe literals,
Unicode, Windows paths, long strings, determinism, atomic write failure,
corrupted labels, changed raw output, invalid saved reports and forged counts.

Evidence-based build improvement: review found that Python equality equated true
and 1, which could incorrectly mark a label correct. Type-sensitive recursive JSON
comparison now distinguishes booleans, integers and floats. The regression test
passes. Saved report counts are also recomputed and checked before rendering.

Real-use accuracy, usage, revenue, buyer demand and savings remain unmeasured.
No real trial results are shipped. The two-week improvement hook and final verdict
remain pending as specified in REVIEW.md. Local acceptance verdict: PASS.
