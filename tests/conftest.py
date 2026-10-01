import json
import pytest
from structured_output_repairer.cli import main
from structured_output_repairer.fixtures import generate

@pytest.fixture
def fixture_run(tmp_path):
    inputs = tmp_path / "inputs"
    results = tmp_path / "results.json"
    generate(inputs)
    assert main(["run", "--input", str(inputs), "--results", str(results)]) == 0
    return inputs, results, json.loads(results.read_text(encoding="utf-8"))
