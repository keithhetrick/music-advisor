"""
Shared helpers for tempo binning and neighbor relationships.

Keep this isolated so changes to binning or neighbor selection don't ripple
through sidecar or overlay code.
"""
from __future__ import annotations

import math
from typing import Dict, Iterable, List, Optional, Sequence, Tuple


def valid_bpm(val: float | int | None) -> bool:
    if val is None:
        return False
    try:
        bpm = float(val)
    except Exception:
        return False
    return 0.0 < bpm < 400.0


def bin_center(bpm: float, bin_width: float) -> float:
    bin_start = math.floor(bpm / bin_width) * bin_width
    return bin_start + (bin_width / 2.0)


def bin_counts(bpms: List[float], bin_width: float) -> Dict[float, int]:
    counts: Dict[float, int] = {}
    for bpm in bpms:
        if not valid_bpm(bpm):
            continue
        center = bin_center(bpm, bin_width)
        counts[center] = counts.get(center, 0) + 1
    return counts


def smooth_counts(counts: Dict[float, int], smoothing: float) -> Dict[float, float]:
    """
    Simple neighbor smoothing: each bin gets blended with adjacent bins.
    smoothing=0.0 => no change; smoothing=0.5 => 50% weight from neighbors average.
    """
    if smoothing <= 1e-9:
        return counts
    smooth: Dict[float, float] = {}
    bins = sorted(counts.keys())
    for i, center in enumerate(bins):
        left = counts.get(bins[i - 1], 0) if i - 1 >= 0 else 0
        right = counts.get(bins[i + 1], 0) if i + 1 < len(bins) else 0
        own = counts.get(center, 0)
        neighbor_avg = (left + right) / 2.0
        smooth[center] = (1 - smoothing) * own + smoothing * neighbor_avg
    raw_total = sum(counts.values()) or 1.0
    smooth_total = sum(smooth.values()) or 1.0
    if abs(smooth_total - raw_total) > 1e-9:
        scale = raw_total / smooth_total
        smooth = {k: v * scale for k, v in smooth.items()}
    return smooth


def smooth_counts_gaussian(counts: Dict[float, int] | Dict[float, float], sigma_bins: float = 1.0) -> Dict[float, float]:
    """
    Gaussian smoothing over sorted centers. sigma_bins is in bin units (1 => 1-bin stddev).
    """
    if sigma_bins <= 1e-9:
        return {k: float(v) for k, v in counts.items()}
    centers = sorted(counts.keys())
    smoothed: Dict[float, float] = {}
    total = sum(counts.values()) or 1.0
    for c in centers:
        weight_sum = 0.0
        val_sum = 0.0
        for c2 in centers:
            z = (c - c2) / sigma_bins
            w = math.exp(-0.5 * z * z)
            weight_sum += w
            val_sum += w * float(counts[c2])
        smoothed[c] = val_sum / weight_sum if weight_sum else 0.0
    smoothed_total = sum(smoothed.values()) or 1.0
    if abs(smoothed_total - total) > 1e-9:
        scale = total / smoothed_total
        smoothed = {k: v * scale for k, v in smoothed.items()}
    return smoothed


def percentile_band(bpms: List[float], lower: float = 0.2, upper: float = 0.8) -> Tuple[float, float]:
    """
    Compute a robust density band (e.g., 20th–80th percentile) to approximate the hit medium.
    """
    if not bpms:
        return (0.0, 0.0)
    ordered = sorted(bpms)
    n = len(ordered)
    def _pct(p: float) -> float:
        idx = max(0, min(n - 1, int(round(p * (n - 1)))))
        return float(ordered[idx])
    return (_pct(lower), _pct(upper))


def _weighted_percentile(values: Sequence[float], weights: Sequence[float], pct: float) -> float:
    pairs = sorted(zip(values, weights), key=lambda x: x[0])
    total = sum(w for _, w in pairs) or 1.0
    target = pct * total
    running = 0.0
    for v, w in pairs:
        running += w
        if running >= target:
            return float(v)
    return float(pairs[-1][0])


def percentile_band_weighted(
    bpms: Sequence[float],
    weights: Optional[Sequence[float]] = None,
    lower: float = 0.2,
    upper: float = 0.8,
) -> Tuple[float, float]:
    if not bpms:
        return (0.0, 0.0)
    if weights is None:
        return percentile_band(list(bpms), lower=lower, upper=upper)
    clean = [(b, w) for b, w in zip(bpms, weights) if valid_bpm(b) and w is not None and w >= 0]
    if not clean:
        return (0.0, 0.0)
    vals, wts = zip(*clean)
    return (
        _weighted_percentile(vals, wts, lower),
        _weighted_percentile(vals, wts, upper),
    )


def neighbor_bins_for(counts: Dict[float, int], song_center: float) -> List[Dict[str, float]]:
    sorted_bins = sorted(counts.keys())
    neighbors: List[Dict[str, float]] = []
    total = sum(counts.values()) or 1
    try:
        idx = sorted_bins.index(song_center)
    except ValueError:
        idx = 0
        for i, c in enumerate(sorted_bins):
            if song_center < c:
                idx = i
                break
        else:
            idx = len(sorted_bins)
    for neighbor_idx in (idx - 1, idx + 1):
        if 0 <= neighbor_idx < len(sorted_bins):
            center = sorted_bins[neighbor_idx]
            count = counts.get(center, 0)
            neighbors.append(
                {
                    "center_bpm": center,
                    "hit_count": count,
                    "percent_of_lane": count / total,
                }
            )
    return neighbors


def neighbor_bins_with_decay(
    counts: Dict[float, float],
    song_center: float,
    steps: int = 2,
    decay: float = 0.5,
) -> List[Dict[str, float]]:
    """
    Returns neighbors up to N steps away with decaying weight.
    """
    sorted_bins = sorted(counts.keys())
    total = sum(counts.values()) or 1.0
    neighbors: List[Dict[str, float]] = []
    if not sorted_bins:
        return neighbors
    try:
        song_idx = sorted_bins.index(song_center)
    except ValueError:
        song_idx = min(range(len(sorted_bins)), key=lambda i: abs(sorted_bins[i] - song_center))
    for step in range(1, steps + 1):
        for offset in (-step, step):
            idx = song_idx + offset
            if 0 <= idx < len(sorted_bins):
                center = sorted_bins[idx]
                count = float(counts.get(center, 0.0))
                neighbors.append(
                    {
                        "center_bpm": center,
                        "hit_count": count,
                        "percent_of_lane": count / total,
                        "step": step,
                        "weight": (decay ** (step - 1)) * (count / total),
                    }
                )
    return neighbors


def adaptive_bin_width(
    bpms: Iterable[float],
    strategy: str = "fd",
    min_width: float = 1.0,
    max_width: float = 6.0,
) -> float:
    """
    Choose a bin width based on data spread. Defaults to Freedman–Diaconis.
    """
    values = [float(b) for b in bpms if valid_bpm(b)]
    if not values:
        return max(min_width, 1.0)
    n = len(values)
    if strategy == "fd":
        ordered = sorted(values)
        q1 = ordered[int(0.25 * (n - 1))]
        q3 = ordered[int(0.75 * (n - 1))]
        iqr = max(1e-9, q3 - q1)
        width = 2 * iqr / (n ** (1 / 3))
    else:
        # Scott's rule
        mean = sum(values) / n
        var = sum((v - mean) ** 2 for v in values) / n
        std = math.sqrt(var)
        width = 3.5 * std / (n ** (1 / 3))
    width = max(min_width, min(max_width, width))
    return width


def trim_outliers(
    bpms: Sequence[float],
    weights: Optional[Sequence[float]] = None,
    lower_pct: float = 0.0,
    upper_pct: float = 0.0,
) -> Tuple[List[float], Optional[List[float]], Dict[str, float]]:
    """
    Trim by percentile; returns cleaned series and stats about removals.
    """
    if lower_pct <= 0 and upper_pct <= 0:
        return list(bpms), list(weights) if weights is not None else None, {"removed": 0, "total": len(bpms)}
    vals = [b for b in bpms if valid_bpm(b)]
    if not vals:
        return [], None, {"removed": len(bpms), "total": len(bpms)}
    lo, hi = percentile_band(vals, lower=lower_pct, upper=1 - upper_pct if upper_pct > 0 else 1.0)
    cleaned_bpms: List[float] = []
    cleaned_weights: Optional[List[float]] = [] if weights is not None else None
    removed = 0
    for idx, b in enumerate(bpms):
        w = weights[idx] if weights is not None and idx < len(weights) else None
        if not valid_bpm(b) or b < lo or b > hi:
            removed += 1
            continue
        cleaned_bpms.append(float(b))
        if cleaned_weights is not None:
            cleaned_weights.append(float(w) if w is not None else 1.0)
    return cleaned_bpms, cleaned_weights, {"removed": removed, "total": len(bpms)}


def fold_bpm_to_range(bpm: float, low: float = 80.0, high: float = 160.0) -> float:
    """
    Fold tempos into a target window by octave (0.5x/2x).
    """
    if not valid_bpm(bpm):
        return bpm
    val = float(bpm)
    while val < low:
        val *= 2.0
    while val > high:
        val /= 2.0
    return val


def fold_series_to_range(bpms: Sequence[float], low: float = 80.0, high: float = 160.0) -> List[float]:
    return [fold_bpm_to_range(b, low=low, high=high) for b in bpms if valid_bpm(b)]


def lane_shape_metrics(counts: Dict[float, float]) -> Dict[str, float]:
    """
    Return simple shape descriptors to help overlays.
    """
    total = sum(counts.values()) or 1.0
    centers = sorted(counts.keys())
    probs = [counts[c] / total for c in centers]
    mean = sum(c * p for c, p in zip(centers, probs))
    variance = sum(((c - mean) ** 2) * p for c, p in zip(centers, probs))
    std = math.sqrt(variance) if variance > 0 else 0.0
    skew = sum(((c - mean) ** 3) * p for c, p in zip(centers, probs)) / (std ** 3 + 1e-12) if std > 0 else 0.0
    kurt = sum(((c - mean) ** 4) * p for c, p in zip(centers, probs)) / (std ** 4 + 1e-12) - 3 if std > 0 else 0.0
    entropy = -sum(p * math.log2(p) for p in probs if p > 0)
    return {
        "mean": mean,
        "std": std,
        "skew": skew,
        "kurtosis": kurt,
        "entropy": entropy,
    }


def find_peak_clusters(
    counts: Dict[float, float],
    bin_width: float,
    max_clusters: int = 3,
) -> List[Dict[str, float]]:
    """
    Identify up to max_clusters contiguous peaks sorted by density.
    """
    if not counts:
        return []
    max_count = max(counts.values())
    if max_count <= 0:
        return []
    centers = sorted(counts.keys())
    clusters: List[List[float]] = []
    # Treat any bin within 1 bin of a max bin as part of candidate clusters
    max_bins = [c for c, v in counts.items() if math.isclose(v, max_count) or v == max_count]
    for c in sorted(max_bins):
        if not clusters or abs(c - clusters[-1][-1]) > bin_width + 1e-9:
            clusters.append([c])
        else:
            clusters[-1].append(c)
    scored: List[Dict[str, float]] = []
    total = sum(counts.values()) or 1.0
    for cluster in clusters:
        span_min = cluster[0] - (bin_width / 2.0)
        span_max = cluster[-1] + (bin_width / 2.0)
        cluster_count = sum(counts.get(c, 0.0) for c in cluster)
        weight = cluster_count / total
        center = (cluster[0] + cluster[-1]) / 2.0
        scored.append(
            {
                "min_bpm": span_min,
                "max_bpm": span_max,
                "center_bpm": center,
                "hit_count": cluster_count,
                "weight": weight,
            }
        )
    scored.sort(key=lambda x: (-x["hit_count"], abs(x["center_bpm"] - centers[len(centers) // 2])))
    return scored[:max_clusters]


def validate_tempo_series(
    bpms: Sequence[float],
    weights: Optional[Sequence[float]] = None,
    min_count: int = 1,
) -> Tuple[List[float], Optional[List[float]], List[str]]:
    warnings: List[str] = []
    cleaned: List[float] = []
    cleaned_weights: Optional[List[float]] = [] if weights is not None else None
    for idx, b in enumerate(bpms):
        if not valid_bpm(b):
            warnings.append(f"invalid_bpm:{b}")
            continue
        cleaned.append(float(b))
        if cleaned_weights is not None:
            w = weights[idx] if weights is not None and idx < len(weights) else 1.0
            cleaned_weights.append(float(w))
    if len(cleaned) < min_count:
        warnings.append(f"insufficient_samples:{len(cleaned)}")
    return cleaned, cleaned_weights, warnings
