import numpy as np
from sklearn.neighbors import NearestNeighbors

def fit_knn(X: np.ndarray, metric: str = "cosine"):
    n_neighbors = min(64, max(8, int(np.sqrt(len(X))) ))
    knn = NearestNeighbors(metric=metric, n_neighbors=n_neighbors, algorithm="auto")
    knn.fit(X)
    return knn

def query_knn(knn, X_ref: np.ndarray, x: np.ndarray, k: int, metric: str):
    # sklearn kneighbors returns distances; convert to cosine similarity if needed
    distances, indices = knn.kneighbors(x.reshape(1,-1), n_neighbors=k, return_distance=True)
    d = distances[0].astype(float)
    idxs = indices[0].astype(int)
    if metric == "cosine":
        sims = 1.0 - d
    else:
        # map a generic distance to similarity proxy
        sims = 1.0 / (1.0 + d)
    return idxs.tolist(), sims.tolist()
