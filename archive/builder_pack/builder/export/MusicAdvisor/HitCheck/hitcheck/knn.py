import numpy as np

def cosine_sim(a: np.ndarray, b: np.ndarray) -> float:
    na = np.linalg.norm(a); nb = np.linalg.norm(b)
    if na == 0 or nb == 0: return 0.0
    return float(np.dot(a, b) / (na * nb))

def nearest_neighbors(xz: np.ndarray, X_ref: np.ndarray, k: int):
    # cosine similarity to all
    sims = np.zeros(len(X_ref), dtype=float)
    for i, ref in enumerate(X_ref):
        sims[i] = cosine_sim(xz, ref)
    # top-k indices
    idx = np.argsort(-sims)[:k]
    return idx, sims[idx]
