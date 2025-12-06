#!/usr/bin/env python3
# lint_snapshot.py — no external dependencies, works on YAML-style JSON files

import sys, os, json, datetime, re

SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "..", "schemas", "trend_snapshot.schema.json")

def load_obj(path):
    text = open(path, "r", encoding="utf-8").read()

    # Native JSON first
    if path.lower().endswith(".json"):
        return json.loads(text)

    # Treat simple YAML as JSON-compatible (quotes optional)
    if path.lower().endswith((".yml", ".yaml")):
        # VERY light "YAML" → JSON-safe transform
        # Only supports key: value lines & lists, which is all we need
        lines = []
        for line in text.splitlines():
            # Convert "key: value" to "key": "value" if missing quotes
            m = re.match(r"(\s*)([A-Za-z0-9_]+):\s*(.*)", line)
            if m:
                indent, key, val = m.groups()

                # Quote key if not quoted
                key = f"\"{key}\""

                # Quote string values (unless number, {, [, null, true, false)
                if val and not re.match(r"[\{\[\d]|true|false|null", val) and not (val.startswith("\"") and val.endswith("\"")):
                    val = f"\"{val}\""

                lines.append(f"{indent}{key}: {val}")
            else:
                lines.append(line)

        yaml_like = "\n".join(lines)

        try:
            return json.loads(re.sub(r"(\w+):", r'"\1":', yaml_like))
        except Exception:
            raise RuntimeError(
                f"YAML parsing failed — snapshots must remain JSON-compatible. "
                f"Offending file: {path}"
            )

    raise RuntimeError("Unsupported file type. Use .yaml, .yml, or .json")

def load_schema():
    return json.load(open(SCHEMA_PATH, "r", encoding="utf-8"))

def is_iso8601(s):
    try:
        datetime.datetime.fromisoformat(s.replace("Z", "+00:00"))
        return True
    except Exception:
        return False

def validate(obj, schema):
    problems = []

    required = ["id", "generated_at", "category", "signals"]
    for key in required:
        if key not in obj:
            problems.append(f"Missing required field: {key}")

    if "generated_at" in obj and not is_iso8601(obj["generated_at"]):
        problems.append("generated_at is not ISO8601")

    if "version" in obj:
        v = str(obj["version"])
        if not re.match(r"\d{4}[-\.]\d{2}[-\.]\d{2}", v):
            problems.append("version should be YYYY.MM.DD")

    if "signals" in obj and not isinstance(obj["signals"], dict):
        problems.append("signals must be an object")

    return problems

def main():
    if len(sys.argv) != 2:
        print("Usage: lint_snapshot.py <snapshot.yaml|json>")
        sys.exit(2)

    path = sys.argv[1]
    if not os.path.exists(path):
        print(f"Not found: {path}")
        sys.exit(2)

    obj = load_obj(path)
    schema = load_schema()
    problems = validate(obj, schema)

    if problems:
        print("SNAPSHOT LINT: FAIL")
        for p in problems:
            print(" -", p)
        sys.exit(1)

    print("SNAPSHOT LINT: OK")
    sys.exit(0)

if __name__ == "__main__":
    main()
