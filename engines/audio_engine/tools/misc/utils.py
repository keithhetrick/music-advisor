import json, pathlib
def read_json(p): return json.loads(pathlib.Path(p).read_text())
def write_json(p, obj): pathlib.Path(p).write_text(json.dumps(obj, indent=2))
