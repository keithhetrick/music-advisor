# Environment Variables

| Variable            | Default              | Purpose                                                               |
| ------------------- | -------------------- | --------------------------------------------------------------------- |
| MA_DATA_ROOT        | `data`               | Base data dir (public/private/features_output); used by path helpers. |
| MA_CALIBRATION_ROOT | `shared/calibration` | Override calibration assets root if needed.                           |
| LOG_REDACT          | unset                | Set `1` to enable redacted logging.                                   |
| LOG_SANDBOX         | unset                | Set `1` to enable sandbox logging.                                    |
| CLEAN_FORCE         | unset                | Set `1` to skip prompt for `make deep-clean` (git clean -xfd).        |
| PYTHON              | `python3`            | Python interpreter used by Make targets.                              |
| BASE_REF            | `origin/main`        | Git ref used by `infra/scripts/test_affected.sh` for changed files.   |
| MA_CONTACT_EMAIL    | `keith@bellweatherstudios.com` | Primary contact email (overrides in tooling/docs).           |
| MA_CONTACT_ALT_EMAIL| `info@bellweatherstudios.com`  | Alternate/general inbox (overrides in tooling/docs).        |
