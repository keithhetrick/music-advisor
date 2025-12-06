from pathlib import Path


def default_norms_path() -> Path:
    cfg = Path(__file__).parent / "default_norms_path.txt"
    if cfg.exists():
        p = cfg.read_text().strip()
        return (Path(__file__).parent.parent.parent / p).resolve()
    return Path()
