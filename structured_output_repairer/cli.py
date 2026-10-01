"""Local-file CLI with named errors and atomic report writes."""
import argparse
import json
import os
from pathlib import Path
import sys
import tempfile
from .core import RepairError, repair, strict_loads, validate
from .fixtures import generate
from .report import render, summarize


def atomic_write(path, text):
    destination = Path(path)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n",
                dir=destination.parent, prefix=".sor-", delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(text)
        os.replace(temporary, destination)
    except OSError as exc:
        raise RepairError(f"WriteError: {destination}: {exc.strerror}") from None
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def read_inputs(directory):
    path = Path(directory)
    if not path.is_dir():
        raise RepairError(f"MissingInput: {path}; use sor fixtures --out demo or provide an input directory")
    rows, errors, seen = [], [], set()
    for file in sorted(path.iterdir()):
        if not file.is_file() or file.name in {"expectations.json", "README.md"}:
            continue
        if file.suffix not in {".json", ".jsonl"}:
            errors.append(f"SchemaError: {file.name}:1: unsupported format; use JSON or JSONL envelopes")
            continue
        try:
            text = file.read_text(encoding="utf-8-sig")
        except (OSError, UnicodeError) as exc:
            errors.append(f"ReadError: {file.name}:1: {type(exc).__name__}")
            continue
        entries = list(enumerate(text.splitlines(), 1)) if file.suffix == ".jsonl" else [(1, text)]
        for line, raw in entries:
            if not raw.strip() or raw.lstrip().startswith("#"):
                continue
            source = f"{file.name}:{line}"
            try:
                row = strict_loads(raw)
                if not isinstance(row, dict):
                    raise RepairError("SchemaError: envelope must be an object")
                required = {"id", "synthetic", "raw"}
                missing = required - row.keys()
                unknown = row.keys() - required - {"expected"}
                if missing or unknown:
                    raise RepairError("SchemaError: fields " + ", ".join(sorted(missing | unknown)))
                if not isinstance(row["id"], str) or not row["id"] or len(row["id"]) > 200:
                    raise RepairError("SchemaError: id must be a nonempty string of at most 200 characters")
                if type(row["synthetic"]) is not bool:
                    raise RepairError("SchemaError: synthetic must be boolean")
                if not isinstance(row["raw"], str):
                    raise RepairError("SchemaError: raw must be a string")
                if row["id"] in seen:
                    raise RepairError("DuplicateId: " + row["id"])
                if "expected" in row:
                    expected = row["expected"]
                    if not isinstance(expected, dict) or set(expected) != {"status", "value"}:
                        raise RepairError("SchemaError: expected requires status and value")
                    if expected["status"] not in {"unchanged", "repaired", "rejected"}:
                        raise RepairError("SchemaError: expected.status")
                    if expected["status"] == "rejected" and expected["value"] is not None:
                        raise RepairError("SchemaError: expected.value must be null for rejected")
                    if expected["status"] != "rejected":
                        if not isinstance(expected["value"], (dict, list)):
                            raise RepairError("SchemaError: expected.value must be object or array")
                        validate(expected["value"], "9999-12-31")
                seen.add(row["id"])
                rows.append({**row, "source": source})
            except json.JSONDecodeError as exc:
                errors.append(f"ParseError: {file.name}:{line + exc.lineno - 1}: column {exc.colno}: {exc.msg}")
            except (RepairError, RecursionError, TypeError) as exc:
                errors.append(f"{source}: {exc}")
    return rows, errors


def parser():
    root = argparse.ArgumentParser(prog="sor", description="Conservative local JSON repair. No model or network calls.")
    commands = root.add_subparsers(dest="command", required=True)
    fixtures = commands.add_parser("fixtures", help="Generate 200 labelled synthetic records", epilog="Example: sor fixtures --out demo")
    fixtures.add_argument("--out", required=True)
    run = commands.add_parser("run", help="Repair JSON/JSONL input envelopes and save measured results", epilog="Example: sor run --input demo")
    run.add_argument("--input", required=True)
    run.add_argument("--results", default=".sor-results.json")
    run.add_argument("--as-of", default="2026-09-30", help="Fixed ISO reference date for future-date validation")
    report = commands.add_parser("report", help="Render measured results with data provenance", epilog="Example: sor report --format md")
    report.add_argument("--format", choices=["md", "json"], default="md")
    report.add_argument("--results", default=".sor-results.json")
    report.add_argument("--out", help="Atomically write instead of printing")
    for name, description in [("repair", "Repair one raw model-output file"), ("validate", "Strictly validate one raw JSON file without repair")]:
        sub = commands.add_parser(name, help=description, epilog=f"Example: sor {name} --file output.txt")
        sub.add_argument("--file", required=True)
        sub.add_argument("--as-of", default="2026-09-30")
    return root


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    args = parser().parse_args(argv)
    try:
        if args.command == "fixtures":
            generate(args.out)
            print("Generated 200 SYNTHETIC records with planted labels and hand-computed expectations.")
        elif args.command == "run":
            from datetime import date
            try:
                date.fromisoformat(args.as_of)
            except ValueError:
                raise RepairError("SchemaError: as_of must be an ISO date") from None
            rows, errors = read_inputs(args.input)
            records = [{**row, "result": repair(row["raw"], args.as_of)} for row in rows]
            result = summarize(records, errors, args.as_of)
            atomic_write(args.results, render(result, "json"))
            print(result["banner"])
            print(json.dumps(result["counts"], sort_keys=True))
            for error in errors:
                print(error.replace(chr(0x2014), "\\u2014"), file=sys.stderr)
            return 2 if errors else 0
        elif args.command == "report":
            result = strict_loads(Path(args.results).read_text(encoding="utf-8"))
            try:
                output = render(result, args.format)
            except (KeyError, TypeError):
                raise RepairError("SchemaError: results do not match sor report schema") from None
            if args.out:
                atomic_write(args.out, output)
            else:
                print(output, end="")
        else:
            from datetime import date
            try:
                date.fromisoformat(args.as_of)
            except ValueError:
                raise RepairError("SchemaError: as_of must be an ISO date") from None
            text = Path(args.file).read_text(encoding="utf-8-sig")
            if args.command == "repair":
                result = repair(text, args.as_of)
            else:
                try:
                    value = strict_loads(text)
                    if not isinstance(value, (dict, list)):
                        raise RepairError("SchemaError: root must be object or array")
                    validate(value, args.as_of)
                    result = {"status": "valid", "value": value, "error": None}
                except json.JSONDecodeError as exc:
                    raise RepairError(f"ParseError: {args.file}:{exc.lineno}: column {exc.colno}: {exc.msg}") from None
            print(json.dumps(result, ensure_ascii=True, sort_keys=True))
            return 2 if result.get("status") == "rejected" else 0
        return 0
    except FileNotFoundError as exc:
        print(f"MissingInput: {exc.filename}; check --file/--results or run sor run --input demo".replace(chr(0x2014), "\\u2014"), file=sys.stderr)
    except json.JSONDecodeError as exc:
        print(f"ParseError: {getattr(args, 'results', '')}:{exc.lineno}: {exc.msg}", file=sys.stderr)
    except (RepairError, OSError, UnicodeError, ValueError, RecursionError) as exc:
        message = str(exc) if isinstance(exc, RepairError) else f"FileError: {exc}"
        print(message.replace(chr(0x2014), "\\u2014"), file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
