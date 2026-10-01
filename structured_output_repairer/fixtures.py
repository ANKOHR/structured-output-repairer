"""Synthetic fixture design, no randomness; seed is not applicable."""
import json
from pathlib import Path

# Eight groups of 25: manually counted, independent of the repair engine.
EXPECTATIONS = {"records": 200, "unchanged": 25, "repaired": 100,
                "rejected": 75, "labelled": 200, "correct": 200,
                "false_positives": 0, "false_negatives": 0}


def generate(out):
    path = Path(out)
    path.mkdir(parents=True, exist_ok=True)
    rows = []
    for group in range(8):
        for index in range(25):
            value = {"name": "Synthetic item " + str(index), "amount": index, "date": "2026-09-01"}
            raw = json.dumps(value, ensure_ascii=False, sort_keys=True)
            status = "unchanged" if group == 0 else "repaired" if group < 5 else "rejected"
            if group == 1:
                raw = "```json\n" + raw + "\n```"
            elif group == 2:
                raw = raw[:-1] + ",}"
            elif group == 3:
                raw = repr(value)
            elif group == 4:
                raw = "Here is the JSON: " + raw
            elif group == 5:
                raw = raw[:-1]
            elif group == 6:
                raw = raw + " " + raw
            elif group == 7:
                raw = '{"amount": -1}'
            rows.append({"id": f"synthetic-{group}-{index:02d}", "synthetic": True,
                         "raw": raw, "expected": {"status": status, "value": value if group < 5 else None}})
    (path / "records.jsonl").write_text("# SYNTHETIC fixtures, planted ground truth\n" +
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows), encoding="utf-8")
    (path / "expectations.json").write_text(json.dumps({"synthetic": True,
        "label": "SYNTHETIC hand-computed expectations: 8 groups x 25",
        "counts": EXPECTATIONS}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
