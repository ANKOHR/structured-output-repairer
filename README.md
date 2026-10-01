# Structured Output Repairer

`sor` is a deterministic Python CLI for conservative recovery of malformed JSON model output. It runs on CPU using the standard library, local files only, with no model calls, network calls, database, or GPU dependencies.

Hypothesis: a tested deterministic CLI can recover defined malformed-output patterns while making unsupported cases explicit. The synthetic acceptance test validates those patterns, not general reliability on unseen model output.

## Quickstart

Python 3.10 or newer and setuptools 68 or newer are required. From this repository:

```powershell
python -m pip install --no-index --no-build-isolation --no-deps -e .
sor fixtures --out demo
sor run --input demo
sor report --format md
python -m pytest -q
```

If the Python Scripts directory is absent from PATH, use `python -m structured_output_repairer.cli` in place of `sor`, or create a virtual environment and activate it before installing. pytest is a development prerequisite, not a runtime dependency. Installation above uses only already installed build tools and performs no network access.

The shell-independent demo is three consecutive commands; in shells supporting `&&`:

```text
sor fixtures --out demo && sor run --input demo && sor report --format md
```

For the smallest version, `examples/tiny/records.jsonl` has five hand-written, synthetic records: valid JSON, code fence, trailing comma, Python literal, and incomplete JSON. Run `sor run --input examples/tiny` then `sor report --format md`. Expected counts: one unchanged, three repaired, one rejected. These are planted synthetic expectations, not real-use performance claims.

## Input format

A directory contains UTF-8 `.jsonl` files (one envelope per line) or `.json` files (one envelope per file). JSONL supports blank lines and `#` comment lines. JSON permits no comments. Files are read in sorted filename order, lines in original order. `expectations.json` and `README.md` are metadata and skipped. Other file formats generate an explicit SchemaError rather than being silently dropped.

```json
{"id":"example-1","synthetic":true,"raw":"{\"amount\": 2,}","expected":{"status":"repaired","value":{"amount":2}}}
```

Required fields:

| Field | Rule |
| --- | --- |
| id | Unique, nonempty string, at most 200 characters |
| synthetic | Explicit boolean; true for fabricated examples |
| raw | Model output as a string, at most 1,000,000 characters |
| expected | Optional hand-checked label with exactly status and value |

Unknown envelope fields, missing fields, duplicate envelope keys and duplicate ids are errors. Errors are included separately in the report and produce exit code 2; they are never silently counted as repaired records. `records` counts successfully parsed envelopes; input error count is separate. A duplicate keeps the first record and reports the subsequent one as an error.

Expected status is `unchanged`, `repaired`, or `rejected`; rejected labels require null value. For accepted labels, value is the hand-checked JSON object or array. Labels are supplied evidence, not automatically verified truth. Editing a label changes correctness measurements; the engine never uses labels to repair output.

Realistic path: Henry may enter his own data by hand in envelopes with `synthetic:false`. Reports identify it as user-declared real input, without claiming authorship or independent verification. No real inputs or trial results ship in this repository. Keep trial files outside version control.

## Repair rules and limits

The root must be an object or array. Supported edits, in a fixed sequence:

1. Remove a whole-output triple-backtick fence, optionally tagged `json`, or the exact prefix `Here is the JSON:`.
2. Remove commas immediately before `}` or `]`, respecting quoted strings and escapes.
3. Parse a safe Python literal and convert it to JSON, if strict JSON still fails. This supports single-quoted strings and Python boolean/null literals. It does not execute expressions.

Valid JSON gets `unchanged`. Applied edits are recorded for every recovery. Whitespace-only normalization is unchanged. Incomplete JSON, multiple objects, unknown prose wrappers, unsupported Python values, duplicate keys and nonfinite numbers are rejected. No missing value, quote, brace, or field is guessed. Objects may have arbitrary fields; no user business schema is inferred.

Generic guards apply recursively to fields called `amount` and `date`: amounts must be numeric, finite and nonnegative (booleans excluded); dates must be ISO dates no later than `--as-of`. The default reference date is fixed at `2026-09-30`, not the machine clock. Use an explicit later date for later real input. Negative amounts such as legitimate refunds are unsupported by this version and explicitly rejected. Unicode and Windows paths are preserved; JSON escapes encode them losslessly. Very deep inputs are rejected rather than causing a traceback. Input size limits are characters, not bytes; envelope files themselves are not streaming-size limited.

## Subcommand catalogue

All commands support `--help` with examples.

| Command | Example | Purpose |
| --- | --- | --- |
| fixtures | `sor fixtures --out demo` | Write labelled 200-record synthetic set and independent expectations |
| run | `sor run --input demo --results results.json` | Compute per-record recovery and measured totals |
| report | `sor report --results results.json --format json --out report.json` | Render JSON or Markdown with provenance |
| repair | `sor repair --file output.txt --as-of 2026-09-30` | Repair one raw model-output file |
| validate | `sor validate --file output.txt` | Strictly validate raw JSON without repair |

Default result file is `.sor-results.json` in the current directory. A report renders saved results; rerun `run` after editing input. `run` exits zero even when raw model output is rejected as an expected domain outcome. It exits 2 on envelope/file errors. `repair` exits 2 for rejected output; `validate` exits 2 for invalid input. Missing paths return MissingInput with a usage hint. Malformed envelope JSON returns ParseError with filename, line and column. Schema drift returns SchemaError with the offending field. Report and result writes use a temporary file in the target directory and atomic replacement; WriteError leaves no partial file and preserves an existing destination. Parent directories must exist.

## Architecture

```text
local JSON/JSONL envelopes
    -> cli.read_inputs (I/O, schema, provenance, named errors)
    -> core.repair (pure deterministic syntax repair and semantic guards)
    -> report.summarize (computed counts and ground-truth comparison)
    -> cli.atomic_write (saved results)
    -> report.render (Markdown or JSON with provenance and record trace)

fixtures.generate -> labelled inputs + independent hand-counted expectations
```

No random generator is used; a seed is not applicable. Dates, filename ordering, JSON key ordering, and line endings are fixed. Identical inputs, options and source filenames produce byte-identical saved results and reports. Runtime is measured separately in evidence, never embedded in deterministic results. Source filenames and line numbers are included for traceability.

## Measured counts

`records = unchanged + repaired + rejected`. `labelled` is the number of supplied labels. `correct` requires exact status and JSON value agreement, including value types: true, 1, and 1.0 are distinct. `false_positives` counts accepted results that disagree with a supplied label (including an accepted value or status mismatch). `false_negatives` counts rejections whose label expected acceptance. A rejected/rejected match is correct; unlabelled records make no accuracy claim. Input errors appear separately with source location. No financial totals or inferred savings exist. Reports recompute saved counts and reject inconsistent result files. This detects accidental edits, not maliciously fabricated source records.

## Honesty boundary and fixture policy

Every report states provenance and separates synthetic ids from user-declared real ids. Any illustrative, hypothetical or unmeasured figure must be described as such. Time saved and money saved are unmeasured and not reported. Execution latency in EVIDENCE.md is a locally measured observation, not a savings claim or a prediction. No hypothetical figures are presented as measured. Synthetic test accuracy does not establish real-use accuracy.

Every generated JSONL fixture has a SYNTHETIC header and each envelope contains `synthetic:true`. JSON metadata contains a synthetic flag and label because JSON does not allow header comments. The tiny hand-written example follows the same policy. Fixture expectations are independent constants: eight groups of 25, producing 25 unchanged, 100 repaired, 75 rejected, 200 correct, zero false positives and zero false negatives. The generator never calls the repair engine to determine labels. Tests corrupt both labels and raw input to demonstrate that reported figures are computed.

## Evidence-based improvement hook and verdict

Use REVIEW.md to record a two-week real-use window starting with the first actual trial, not the build date. Metric: exact status and value accuracy against a hand-checked sample, with sample size, errors, error categories and actual run count. If the measured error rate exceeds 10 percent, fix the leading failure cause or record a kill decision. If there is no actual use in the window, record kill with the reason. Add one measured improvement and before/after sample results if continued.

The final verdict is deliberately pending that window. Choose expand for daily use or revenue, integrate for heavy sibling overlap, commercialise for evidenced buyer willingness to pay as-is, maintain for portfolio evidence if used but no stronger case, or kill for no use or unmet acceptance criteria. Local fixture acceptance alone does not justify a commercial claim.

See EVIDENCE.md for local acceptance measurements and LESSONS.md for build lessons. Publishing is a separate verification step and is not performed by this build.
