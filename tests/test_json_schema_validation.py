import json
from pathlib import Path
from jsonschema import Draft7Validator


def _load(path: Path):
    return json.loads(path.read_text())


def test_pack_schema_valid():
    schema = _load(Path("schemas/pack.schema.json"))
    Draft7Validator.check_schema(schema)
    # Validate a minimal pack shape produced by pack_writer
    instance = {
        "region": "US",
        "profile": "Pop",
        "generated_by": "pack_writer",
        "audio_name": "song",
        "inputs": {
            "paths": {"source_audio": "song.wav"},
            "merged_features_present": True,
            "lyric_axis_present": False,
            "internal_features_present": True,
        },
        "features": {
            "tempo_bpm": 120.0,
            "key": "C",
            "mode": "major",
            "runtime_sec": 180.0,
            "loudness_LUFS": -10.0,
        },
        "features_full": {
            "bpm": 120.0,
            "mode": "major",
            "key": "C",
            "duration_sec": 180.0,
            "loudness_lufs": -10.0,
        },
    }
    Draft7Validator(schema).validate(instance)


def test_neighbors_schema_minimal():
    schema = _load(Path("schemas/neighbors.schema.json"))
    Draft7Validator.check_schema(schema)
    instance = {"neighbors": [{"tier": "tier1_modern", "distance": 0.1}]}
    Draft7Validator(schema).validate(instance)


def test_run_summary_schema_minimal():
    schema = _load(Path("schemas/run_summary.schema.json"))
    Draft7Validator.check_schema(schema)
    instance = {"out_dir": "tmp", "pipeline_version": "test", "versions": {}, "warnings": [], "artifacts": {}}
    Draft7Validator(schema).validate(instance)
