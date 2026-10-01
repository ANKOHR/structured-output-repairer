import json
from structured_output_repairer.fixtures import generate, EXPECTATIONS
from structured_output_repairer.core import repair


def test_fixtures_labelled_synthetic(tmp_path):
    generate(tmp_path)
    lines = (tmp_path / "records.jsonl").read_text(encoding="utf-8").splitlines()
    assert lines[0].startswith("# SYNTHETIC")
    assert len(lines[1:]) == 200
    assert all(json.loads(line)["synthetic"] is True for line in lines[1:])
    assert json.loads((tmp_path / "expectations.json").read_text())["synthetic"] is True


def test_fixture_ground_truth_matches_hand_computed(tmp_path):
    generate(tmp_path)
    counts = {"unchanged":0, "repaired":0, "rejected":0}
    for line in (tmp_path / "records.jsonl").read_text().splitlines()[1:]:
        row = json.loads(line)
        result = repair(row["raw"])
        assert {"status": result["status"], "value": result["value"]} == row["expected"]
        counts[result["status"]] += 1
    assert counts == {"unchanged":25, "repaired":100, "rejected":75}
    assert EXPECTATIONS["records"] == 200


def test_fixture_determinism(tmp_path):
    generate(tmp_path / "a")
    generate(tmp_path / "b")
    for name in ["records.jsonl", "expectations.json"]:
        assert (tmp_path / "a" / name).read_bytes() == (tmp_path / "b" / name).read_bytes()
