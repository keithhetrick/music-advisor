# SBOM (Software Bill of Materials)

Generate a headless SBOM for the current environment (optional, but recommended for releases).

## Generate (CycloneDX)

```bash
python -m pip install cyclonedx-bom
PYTHONPATH=. python -m cyclonedx_py --format json --outfile docs/sbom/sbom.json
```

## Make target

```bash
make sbom
```

## Notes

- SBOM generation is optional and can be run locally before tagging a release.
- Keep `docs/sbom/` checked in for visibility if you generate a fresh SBOM.
