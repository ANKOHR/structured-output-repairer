import pytest
from structured_output_repairer.core import repair

@pytest.mark.parametrize("raw", ['{"a":1}', '[1,2]', '{"s":",} string",}', "{'a': 1}", '```json\n{"a":1}\n```', 'Here is the JSON: {"a":1}'])
def test_recovery(raw):
    assert repair(raw)["status"] != "rejected"

@pytest.mark.parametrize("raw", ['{"amount":-1}', '{"amount":true}', '{"date":"2099-01-01"}', '{"a":1,"a":2}', "{'a':1,'a':2}", '{"a":NaN}', '{"a":1e999}', '{"a":', '{} {}', "{'a': (1,2)}", "__import__('os').system('echo unsafe')", '"scalar"', '{"x": {1:2}}'])
def test_rejects_adversarial_values(raw):
    assert repair(raw)["status"] == "rejected"


def test_handles_unicode_and_long_inputs():
    import json
    value = {"text": "你好 café 😀" * 10000, "path": r"C:\Users\henry\input.json"}
    assert repair(json.dumps(value, ensure_ascii=False))["value"] == value


def test_string_content_never_edited():
    assert repair('{"text": "a,}b,]",}')['value'] == {"text":"a,}b,]"}


def test_extreme_string_limit():
    assert repair("x" * 1000001)["error"].startswith("InputTooLong")


def test_single_quoted_string_content_never_edited():
    assert repair("{'text': ',} and ,]',}")['value'] == {'text': ',} and ,]'}
