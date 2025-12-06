#!/usr/bin/env python3
import argparse, json, sys, re
from datetime import datetime

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def try_jsonschema_validate(data, schema):
    try:
        import jsonschema
        from jsonschema import Draft7Validator
    except Exception as e:
        return False, [f"jsonschema not available: {e}"]
    try:
        Draft7Validator.check_schema(schema)
        v = Draft7Validator(schema)
        errors = sorted(v.iter_errors(data), key=lambda e: e.path)
        if errors:
            msgs = []
            for e in errors:
                loc = "/".join([str(p) for p in e.path]) or "(root)"
                msgs.append(f"[SCHEMA] {loc}: {e.message}")
            return False, msgs
        return True, []
    except Exception as e:
        return False, [f"Schema validation failed: {e}"]

def is_iso8601(s):
    try:
        if s.endswith("Z"):
            datetime.fromisoformat(s.replace("Z", "+00:00"))
        else:
            datetime.fromisoformat(s)
        return True
    except Exception:
        return False

def normalize_tempo_string(s):
    return s.replace("–", "-").replace("—", "-")

def structural_checks(data, strict=False):
    errs = []
    if "region" not in data or not data["region"]:
        errs.append("Missing 'region'.")
    if "generated_at" not in data or not is_iso8601(data["generated_at"]):
        errs.append("Invalid or missing 'generated_at'.")
    mn = data.get("MARKET_NORMS", {})
    if not isinstance(mn, dict) or "profile" not in mn:
        errs.append("Missing 'MARKET_NORMS.profile'.")

    mvp = data.get("MVP", {})
    tempo = mvp.get("tempo_band_bpm")
    runtime = mvp.get("runtime_sec")
    ttc = mvp.get("ttc_sec")
    exposures = mvp.get("exposures")

    if tempo is None:
        errs.append("Missing 'tempo_band_bpm'.")
    elif isinstance(tempo, str):
        if not re.match(r"^[0-9]{2,3}-[0-9]{2,3}$", normalize_tempo_string(tempo)):
            errs.append("Bad 'tempo_band_bpm' string.")
    elif isinstance(tempo, (int, float)) and not (40 <= tempo <= 220):
        errs.append("Bad numeric tempo.")
    elif not isinstance(tempo, (str, int, float)):
        errs.append("Invalid tempo type.")

    if not isinstance(runtime, (int, float)):
        errs.append("Missing or invalid 'runtime_sec'.")

    if strict:
        base = data.get("Baseline")
        if not isinstance(base, dict):
            errs.append("Missing 'Baseline' object.")
        else:
            if "active_profile" not in base:
                errs.append("Baseline.active_profile required.")
            if "effective_utc" not in base or not is_iso8601(str(base.get('effective_utc', ''))):
                errs.append("Baseline.effective_utc must be ISO.")
            if "pinned" not in base or not isinstance(base["pinned"], bool):
                errs.append("Baseline.pinned must be boolean.")
    return errs

def apply_autofix(data):
    notes = []
    if "MVP" not in data:
        mvp = {
            "tempo_band_bpm": data.get("tempo_band_bpm"),
            "runtime_sec": data.get("runtime_sec"),
            "ttc_sec": data.get("ttc_sec"),
            "exposures": data.get("exposures")
        }
        data["MVP"] = mvp
        notes.append("Created MVP block.")
    tb = data["MVP"].get("tempo_band_bpm")
    if isinstance(tb, str):
        fixed = normalize_tempo_string(tb)
        if fixed != tb:
            data["MVP"]["tempo_band_bpm"] = fixed
            notes.append("Normalized tempo hyphen.")
    if "Baseline" not in data:
        data["Baseline"] = {
            "active_profile": data.get("MARKET_NORMS", {}).get("profile"),
            "effective_utc": data.get("generated_at"),
            "pinned": False
        }
        notes.append("Added Baseline skeleton.")
    if "Known_Gaps" not in data:
        data["Known_Gaps"] = []
        notes.append("Added Known_Gaps.")
    return data, notes

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pack")
    ap.add_argument("--schema")
    ap.add_argument("--strict", action="store_true")
    ap.add_argument("--autofix", action="store_true")
    ap.add_argument("--out")
    args = ap.parse_args()
    try:
        data = load_json(args.pack)
    except Exception as e:
        print(f"[FATAL] {e}", file=sys.stderr)
        sys.exit(2)
    schema = None
    if args.schema:
        try:
            schema = load_json(args.schema)
        except Exception as e:
            print(f"[WARN] Schema read failed: {e}")
    schema_ok, schema_msgs = True, []
    if schema:
        schema_ok, schema_msgs = try_jsonschema_validate(data, schema)
    struct_errs = structural_checks(data, strict=args.strict)
    notes = []
    if args.autofix:
        data, notes = apply_autofix(data)
        struct_errs = structural_checks(data, strict=args.strict)
    for m in schema_msgs: print(m)
    for e in struct_errs: print(f"[STRUCT] {e}")
    for n in notes: print(f"[AUTOFIX] {n}")
    if args.out and (args.autofix or not struct_errs):
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        print(f"[OK] wrote {args.out}")
    if (not schema_ok) or struct_errs:
        sys.exit(1)
    sys.exit(0)

if __name__ == "__main__":
    main()
