"""Pure repair functions. Never invent missing values or close truncated JSON."""
import ast
import json
import math
import re
from datetime import date

MAX_INPUT = 1_000_000

class RepairError(ValueError):
    """Named failure safe to show in a CLI."""


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise RepairError("DuplicateKey: " + key)
        result[key] = value
    return result


def strict_loads(text):
    return json.loads(text, object_pairs_hook=_pairs,
                      parse_constant=lambda value: (_ for _ in ()).throw(
                          RepairError("NonFiniteNumber: " + value)))


def validate(value, as_of="2026-09-30"):
    """Generic JSON plus optional amount/date semantic guards, fixed reference date."""
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise RepairError("SchemaError: object keys must be strings")
            if key == "amount" and (isinstance(item, bool) or not isinstance(item, (int, float)) or item < 0):
                raise RepairError("SchemaError: amount must be a nonnegative number")
            if key == "date":
                try:
                    parsed = date.fromisoformat(item)
                except (TypeError, ValueError):
                    raise RepairError("SchemaError: date must be an ISO date") from None
                if parsed > date.fromisoformat(as_of):
                    raise RepairError("SchemaError: date exceeds as_of " + as_of)
            validate(item, as_of)
    elif isinstance(value, list):
        for item in value:
            validate(item, as_of)
    elif isinstance(value, float) and not math.isfinite(value):
        raise RepairError("NonFiniteNumber: value")
    elif value is not None and not isinstance(value, (str, int, float, bool)):
        raise RepairError("SchemaError: unsupported JSON value")


def _remove_trailing_commas(text):
    # Scan strings so a comma inside a quoted string is never edited.
    out = []
    quote = None
    escaped = False
    for pos, char in enumerate(text):
        if quote is None and char == ",":
            following = pos + 1
            while following < len(text) and text[following].isspace():
                following += 1
            if following < len(text) and text[following] in "}]":
                continue
        out.append(char)
        if quote is not None:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
        elif char in ('"', "'"):
            quote = char
    return "".join(out)


def repair(raw, as_of="2026-09-30"):
    """Return status, value and auditable edits; reject ambiguous or missing data."""
    try:
        date.fromisoformat(as_of)
        if not isinstance(raw, str):
            raise RepairError("SchemaError: raw must be a string")
        if len(raw) > MAX_INPUT:
            raise RepairError("InputTooLong: maximum 1000000 characters")
        text = raw.strip()
        edits = []
        try:
            value = strict_loads(text)
        except json.JSONDecodeError:
            match = re.fullmatch(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
            if match:
                text = match.group(1).strip()
                edits.append("remove_code_fence")
            elif text.startswith("Here is the JSON:"):
                text = text[len("Here is the JSON:"):].strip()
                edits.append("remove_known_prefix")
            cleaned = _remove_trailing_commas(text)
            if cleaned != text:
                edits.append("remove_trailing_commas")
                text = cleaned
            try:
                value = strict_loads(text)
            except json.JSONDecodeError:
                # Literal parsing is safe, but only string-key JSON-shaped literals pass.
                tree = ast.parse(text, mode="eval")
                for node in ast.walk(tree):
                    if isinstance(node, ast.Dict):
                        keys = [ast.literal_eval(key) for key in node.keys]
                        if len(keys) != len(set(keys)):
                            raise RepairError("DuplicateKey: literal object")
                value = ast.literal_eval(tree)
                edits.append("convert_python_literal")
        if not isinstance(value, (dict, list)):
            raise RepairError("SchemaError: root must be object or array")
        validate(value, as_of)
        # Reparse to enforce serializable JSON and reject unsupported Python literals.
        strict_loads(json.dumps(value, allow_nan=False))
        return {"status": "repaired" if edits else "unchanged", "value": value, "edits": edits, "error": None}
    except (RepairError, ValueError, TypeError, SyntaxError, RecursionError, OverflowError) as exc:
        error = str(exc) if isinstance(exc, RepairError) else "UnrecoverableOutput: invalid, ambiguous or incomplete JSON"
        return {"status": "rejected", "value": None, "edits": [], "error": error}
