# Security Policy

- **Reporting**: Please report vulnerabilities privately to the maintainers (no public issues). Include reproduction steps, impact, and any logs (with sensitive data removed). Contact: `security@music-advisor.dev` (example) with “SECURITY” in the subject. Expected initial response: within 3 business days.
- **No secrets**: Do not commit credentials, presigned URLs, or private dataset links. Manifests should only reference public, sanitized assets.
- **Supported branch**: `main` is the active branch. Older tags are archived and not patched.
- **Data safety**: Default `MA_DATA_ROOT` points to `data/`; contents are git-ignored. Only sanitized public assets should be fetched via `infra/scripts/data_manifest.json`.
