import json
d = json.load(open("Knowledge/emotional_axes.json"))
assert "axes" in d and "defaults" in d
for k,v in d["defaults"].items():
    assert 0 <= v <= 100
print("emotional_axes.json OK")
