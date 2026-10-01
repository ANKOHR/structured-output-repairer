# Lessons for KOML

The synthetic fixture supports the narrow assumption that common wrapper and delimiter defects can be repaired deterministically without inventing values. It does not validate recovery of arbitrary malformed output. Truncation and multiple candidates require rejection because syntactic plausibility is not evidence of the intended value.

Ground-truth mutation tests showed that reported correctness and false positives change when a supplied label changes. Raw-output mutation showed that recovery totals change when the input changes. This validates computed reporting rather than hardcoded acceptance numbers. Real-use accuracy and buyer demand remain unmeasured.

An initial test used a million-character parameter as its test id. Windows temporary-path handling failed before that case ran. Giving the extreme-string case its own short test name corrected the harness. Resource-boundary tests need bounded identifiers as well as bounded engine behavior.

Operating rule: separate deterministic syntax repairs from unknown-value reconstruction, keep expected labels independent of the implementation, and reject uncertainty with a named reason. Do not turn synthetic acceptance into a claim of real-world reliability.

Build review exposed another boundary: Python equality considers True equal to 1.
Exact ground-truth evaluation now compares JSON types recursively, with a regression
test. Saved report totals are recomputed before rendering so edited aggregate counts
cannot masquerade as computed evidence. This checks internal consistency, not the
authenticity of user-supplied records or labels.
