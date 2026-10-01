import json
import subprocess
import sys
import time
import pytest
from structured_output_repairer.cli import main


def test_run_completes_on_fixture(fixture_run):
    inputs, results, _ = fixture_run
    start = time.perf_counter()
    assert main(["run", "--input", str(inputs), "--results", str(results)]) == 0
    assert main(["report", "--results", str(results), "--out", str(inputs.parent / "report.md")]) == 0
    assert time.perf_counter() - start < 5


def test_empty_input_renders_without_traceback(tmp_path, capsys):
    results = tmp_path / "results.json"
    inputs = tmp_path / "empty"; inputs.mkdir()
    assert main(["run", "--input", str(inputs), "--results", str(results)]) == 0
    assert main(["report", "--results", str(results)]) == 0
    assert json.loads(results.read_text())["counts"]["records"] == 0
    assert "Traceback" not in capsys.readouterr().out

@pytest.mark.parametrize("name,raw", [("bad.json", '{\n"raw":'), ("bad.jsonl", '# comment\n{'), ("bad.csv", 'bad,csv'), ("bad.yaml", 'bad: [')])
def test_malformed_input_named_error(tmp_path, capsys, name, raw):
    inputs = tmp_path / "input"; inputs.mkdir()
    (inputs / name).write_text(raw)
    assert main(["run", "--input", str(inputs), "--results", str(tmp_path / "r.json")]) == 2
    err = capsys.readouterr().err
    assert name in err and "Error" in err and ":" in err


def test_determinism_byte_identical(fixture_run):
    inputs, results, _ = fixture_run
    before = results.read_bytes()
    main(["run", "--input", str(inputs), "--results", str(results)])
    assert results.read_bytes() == before


def test_cli_smoke_all_subcommands(tmp_path):
    for command in ["fixtures", "run", "report", "repair", "validate"]:
        completed = subprocess.run([sys.executable, "-m", "structured_output_repairer.cli", command, "--help"], capture_output=True, text=True)
        assert completed.returncode == 0 and "Example:" in completed.stdout
    assert main(["fixtures", "--out", str(tmp_path / "data")]) == 0
    raw = tmp_path / "raw.txt"; raw.write_text('{"ok":true}')
    assert main(["repair", "--file", str(raw)]) == 0
    assert main(["validate", "--file", str(raw)]) == 0
    raw.write_text('{"ok":true,}')
    assert main(["validate", "--file", str(raw)]) == 2


def test_schema_drift_and_duplicate_ids(tmp_path):
    inputs = tmp_path / "input"; inputs.mkdir()
    row = {"id":"a", "synthetic":False, "raw":"{}"}
    (inputs / "records.jsonl").write_text("\n".join(map(json.dumps, [row, row, {"id":"b", "raw":"{}"}])))
    results = tmp_path / "r.json"
    assert main(["run", "--input", str(inputs), "--results", str(results)]) == 2
    report = json.loads(results.read_text())
    assert len(report["input_errors"]) == 2
    assert report["counts"]["records"] == 1
    assert report["provenance"]["user_declared_real_ids"] == ["a"]


def test_missing_input(tmp_path, capsys):
    assert main(["run", "--input", str(tmp_path / "missing")]) == 2
    assert "MissingInput" in capsys.readouterr().err


def test_report_write_failure_no_partial_files(fixture_run, tmp_path, capsys):
    out = tmp_path / "absent" / "report.md"
    assert main(["report", "--results", str(fixture_run[1]), "--out", str(out)]) == 2
    assert "WriteError" in capsys.readouterr().err
    assert not out.exists()
    assert not list(tmp_path.glob(".sor-*"))


def test_tiny_hand_written_demo(tmp_path):
    results = tmp_path / "tiny.json"
    assert main(["run", "--input", "examples/tiny", "--results", str(results)]) == 0
    counts = json.loads(results.read_text())["counts"]
    assert counts == {"records":5,"unchanged":1,"repaired":3,"rejected":1,"labelled":5,"correct":5,"false_positives":0,"false_negatives":0}


def test_write_failure_preserves_existing_destination(fixture_run, monkeypatch, tmp_path):
    import structured_output_repairer.cli as cli
    target = tmp_path / "report.md"
    target.write_text("previous")
    def fail(*args):
        raise OSError("injected replacement failure")
    monkeypatch.setattr(cli.os, "replace", fail)
    assert main(["report", "--results", str(fixture_run[1]), "--out", str(target)]) == 2
    assert target.read_text() == "previous"
    assert not list(tmp_path.glob(".sor-*"))


@pytest.mark.parametrize("payload", [[], {}, {"counts": {"records": 3}}])
def test_malformed_saved_report_named_error(tmp_path, capsys, payload):
    results = tmp_path / "results.json"
    results.write_text(json.dumps(payload))
    for format in ["md", "json"]:
        assert main(["report", "--results", str(results), "--format", format]) == 2
        assert "SchemaError" in capsys.readouterr().err


def test_invalid_expected_value_named_field(tmp_path, capsys):
    row = {"id": "a", "synthetic": True, "raw": "{}",
           "expected": {"status": "unchanged", "value": 1}}
    (tmp_path / "input.json").write_text(json.dumps(row))
    assert main(["run", "--input", str(tmp_path), "--results", str(tmp_path.parent / "r.json")]) == 2
    assert "expected.value" in capsys.readouterr().err


def test_unicode_error_name_is_escaped(tmp_path, capsys):
    (tmp_path / ("bad" + chr(0x2014) + ".json")).write_text("{")
    results = tmp_path.parent / "unicode-results.json"
    assert main(["run", "--input", str(tmp_path), "--results", str(results)]) == 2
    assert chr(0x2014) not in capsys.readouterr().err
    assert main(["report", "--results", str(results)]) == 0
    assert chr(0x2014) not in capsys.readouterr().out
