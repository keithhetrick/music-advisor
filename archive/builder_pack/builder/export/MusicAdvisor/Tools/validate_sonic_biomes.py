import json
j = json.load(open("Knowledge/sonic_biomes.json"))
assert "neighbors" in j and "palette" in j and "space" in j
print("sonic_biomes.json OK")
