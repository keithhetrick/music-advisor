# CI Overview

- Workflow: `.github/workflows/ci.yml`
- Triggers: push and pull_request
- Jobs: `quick-check` on ubuntu-latest
- Steps:
  - Checkout
  - Setup Python 3.11 (pip cache)
  - Install deps: `requirements.txt`, `requirements.lock` (best effort), `engines/audio_engine/requirements.txt` (best effort)
  - Run `./infra/scripts/quick_check.sh`

Local equivalent: `make quick-check` or `./infra/scripts/quick_check.sh`.
