# Docker / Container Notes

No images are published yet. If you containerize:

- Base on python:3.11-slim (install ffmpeg/librosa deps as needed).
- Copy repo, install `requirements.txt` (and engine-specific if needed).
- Mount data via `MA_DATA_ROOT` (e.g., `/app/data`) and keep it a writable volume.
- Do not bake private data into images; use manifests/bootstrap for public assets.

Sample dev build (not published):

```bash
docker build -t music-advisor-dev -f infra/docker/Dockerfile .
```

If you add Dockerfiles, keep them under `infra/docker/` and document entrypoints.
