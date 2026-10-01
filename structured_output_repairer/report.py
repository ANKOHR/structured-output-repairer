"""Measured counts only. No time or money savings are inferred."""
import json
from .core import RepairError


def exact_value(left, right):
    """Compare JSON values without treating true as the number 1."""
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        return left.keys() == right.keys() and all(exact_value(left[k], right[k]) for k in left)
    if isinstance(left, list):
        return len(left) == len(right) and all(exact_value(a, b) for a, b in zip(left, right))
    return left == right


def summarize(records, errors, as_of):
    counts = {key: 0 for key in ("records", "unchanged", "repaired", "rejected", "labelled", "correct", "false_positives", "false_negatives")}
    counts["records"] = len(records)
    for row in records:
        result = row["result"]
        counts[result["status"]] += 1
        expected = row.get("expected")
        if expected is not None:
            counts["labelled"] += 1
            correct = result["status"] == expected["status"] and exact_value(result["value"], expected["value"])
            counts["correct"] += int(correct)
            counts["false_positives"] += int(not correct and result["status"] != "rejected")
            counts["false_negatives"] += int(not correct and result["status"] == "rejected" and expected["status"] != "rejected")
    synthetic = [row["id"] for row in records if row["synthetic"]]
    real = [row["id"] for row in records if not row["synthetic"]]
    return {"banner": "Data provenance: synthetic fixtures are explicitly labelled; real inputs are user-declared, not independently verified.",
            "provenance": {"synthetic_ids": synthetic, "user_declared_real_ids": real},
            "counts": counts, "input_errors": errors, "as_of": as_of, "records": records,
            "honesty": "Counts are measured from inputs. Accuracy applies only to supplied labels. Time saved and money saved are unmeasured and are not reported. No hypothetical figures are presented as measured."}


def render(report, format):
    try:
        computed = summarize(report["records"], report["input_errors"], report["as_of"])
        if not exact_value(report, computed):
            raise ValueError("inconsistent results")
    except (KeyError, TypeError, AttributeError, ValueError):
        raise RepairError("SchemaError: results do not match sor report schema or computed counts") from None
    if format == "json":
        return json.dumps(report, ensure_ascii=True, indent=2, sort_keys=True) + "\n"
    lines = ["# Structured Output Repairer", "", report["banner"], "", report["honesty"], "",
             "Reference date: " + report["as_of"], "", "| Measured count | Value |", "| --- | ---: |"]
    lines += [f"| {key} | {value} |" for key, value in report["counts"].items()]
    lines += ["", "Input errors: " + str(len(report["input_errors"])), ""]
    lines += ["- " + json.dumps(error, ensure_ascii=True) for error in report["input_errors"]]
    lines += ["", "Per-record trace (id, source, status, edits, error):", ""]
    for row in report["records"]:
        result = row["result"]
        lines.append(json.dumps({"id": row["id"], "source": row["source"], "synthetic": row["synthetic"], **result}, ensure_ascii=True, sort_keys=True))
    return "\n".join(lines) + "\n"
