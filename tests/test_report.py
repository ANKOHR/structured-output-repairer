import json
from structured_output_repairer.fixtures import EXPECTATIONS
from structured_output_repairer.report import render
from structured_output_repairer.cli import main


def test_report_matches_ground_truth_exact(fixture_run):
    assert fixture_run[2]["counts"] == EXPECTATIONS


def test_report_zero_false_positives(fixture_run):
    assert fixture_run[2]["counts"]["false_positives"] == 0
    assert fixture_run[2]["counts"]["correct"] == 200


def test_report_carries_provenance_banner(fixture_run):
    for format in ["md", "json"]:
        text = render(fixture_run[2], format)
        assert "Data provenance:" in text
        assert "synthetic" in text
        assert "user-declared" in text


def test_hypothetical_figures_labelled(fixture_run):
    for format in ["md", "json"]:
        text = render(fixture_run[2], format)
        assert "Time saved and money saved are unmeasured" in text
        assert "No hypothetical figures are presented as measured" in text


def test_no_em_dashes_in_outputs(fixture_run):
    for format in ["md", "json"]:
        assert chr(0x2014) not in render(fixture_run[2], format)


def test_corrupted_ground_truth_changes_measured_counts(fixture_run):
    inputs, results, before = fixture_run
    file = inputs / "records.jsonl"
    lines = file.read_text().splitlines()
    row = json.loads(lines[1])
    row["expected"]["value"]["amount"] = 100
    lines[1] = json.dumps(row)
    file.write_text("\n".join(lines) + "\n")
    assert main(["run", "--input", str(inputs), "--results", str(results)]) == 0
    after = json.loads(results.read_text())
    assert after["counts"]["correct"] == 199
    assert after["counts"]["false_positives"] == 1
    assert before["counts"]["false_positives"] == 0


def test_changed_raw_changes_repair_counts(fixture_run):
    inputs, results, _ = fixture_run
    file = inputs / "records.jsonl"
    lines = file.read_text().splitlines()
    row = json.loads(lines[1]); row["raw"] = '{"amount":-2}'
    lines[1] = json.dumps(row)
    file.write_text("\n".join(lines) + "\n")
    main(["run", "--input", str(inputs), "--results", str(results)])
    counts = json.loads(results.read_text())["counts"]
    assert counts["rejected"] == 76 and counts["unchanged"] == 24


def test_exact_values_distinguish_boolean_and_number():
    from structured_output_repairer.report import exact_value
    assert not exact_value({"x": True}, {"x": 1})
    assert not exact_value([1], [1.0])
    assert exact_value({"x": [1, True]}, {"x": [1, True]})


def test_saved_counts_cannot_be_forged(fixture_run):
    import pytest
    from structured_output_repairer.core import RepairError
    report = fixture_run[2]
    report["counts"]["correct"] = 999
    for format in ["md", "json"]:
        with pytest.raises(RepairError, match="SchemaError"):
            render(report, format)
