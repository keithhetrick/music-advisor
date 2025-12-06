# Payload Contract v0.3.5 (BuilderPack)

This spec defines the JSON the GPT expects when the external AudioTools pipeline is used.

- Schema: `contracts/schema/audiotools_payload_v0.3.5.schema.json`
- Example: `contracts/examples/audiotools_payload_v0.3.5.json`

**Breaking change note:** TTC moved to a nested `TTC` object; legacy flat keys (`ttc_sec`, `ttc_conf`) are deprecated.
