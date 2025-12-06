import json, sys
j = json.load(open("Knowledge/listener_archetypes.json"))
assert isinstance(j, dict)
for k, v in j.items():
    for f in ("lyric","arr","avoid","freq"):
        assert f in v and isinstance(v[f], str), f"Missing {f} in {k}"
print("listener_archetypes.json OK")
