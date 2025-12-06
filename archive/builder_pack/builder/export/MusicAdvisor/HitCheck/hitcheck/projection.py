import numpy as np

def hci_v1_projection(neighbor_hci: np.ndarray, neighbor_sims: np.ndarray,
                      cohort_hci_mean: float, alpha: float = 0.12, lambd: float = 0.08) -> float:
    """
    HCI_v1p = blend( similarity-weighted neighbor HCI, cohort mean ).
    alpha = weight for similarity-weighted neighbor mean
    lambda = additional pull toward cohort mean for stability
    """
    if neighbor_hci.size == 0:
        return float(cohort_hci_mean)
    # similarity weights (normalize)
    w = neighbor_sims.clip(min=0)
    if w.sum() <= 1e-9:
        w = np.ones_like(w)
    w = w / (w.sum() + 1e-9)
    local = float((neighbor_hci * w).sum())
    # blend toward cohort mean
    proj = (1 - alpha) * local + alpha * cohort_hci_mean
    # additional small pull (stability)
    proj = (1 - lambd) * proj + lambd * cohort_hci_mean
    return float(proj)
