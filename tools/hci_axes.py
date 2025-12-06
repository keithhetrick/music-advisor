# tools/hci_axes.py
from __future__ import annotations
import json, math
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

# --------------------------------------------------------------------
# Core helpers
# --------------------------------------------------------------------

def _gaussian_fit(x: Optional[float], mean: Optional[float], std: Optional[float]) -> float:
    """
    Simple Gaussian fit used for:
      - Tempo_Fit
      - Runtime_Fit
      - Loudness_Fit

    Returns a value in (0, 1] (with 1.0 at mean, decaying as x moves away).
    If mean or std are missing/invalid, returns 0.5 as a neutral fallback.
    """
    try:
        if x is None or mean is None or std is None or std <= 0:
            return 0.5
        z = (x - mean) / std
        # exp(-0.5 z^2) but scaled a bit so moderate deviation gives ~0.7–0.8
        return float(math.exp(-0.5 * (z ** 2)))
    except Exception:
        return 0.5


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, float(x)))


def _compute_valence_axis(features_full: Dict[str, Any]) -> float:
    """
    Compute a locally-defined Valence axis on [0,1] from basic audio features.

    This is an *audio brightness / emotional tone* proxy, not a lyric sentiment
    score. It intentionally uses only features that are already present in
    features_full:

        - mode            – "major" / "minor" / other
        - tempo_bpm       – used as a weak bias around the ~112 BPM pop mean
        - energy          – 0..1 overall energy envelope
        - danceability    – 0..1 groove / movement
        - valence         – legacy estimator from the feature extractor

    Heuristic:

        1. Center energy, danceability and legacy valence around 0.5.
        2. Compute a small tempo offset around 112 BPM so mid-up tempos lean
           slightly brighter.
        3. Apply a mild major/minor bias (major → +0.08, minor → -0.08).
        4. Combine into a raw score:

               score =
                 0.25 * legacy_c +
                 0.25 * energy_c +
                 0.35 * dance_c +
                 0.05 * tempo_c +
                 mode_bias

        5. Map score into [0,1] via an affine transform around 0.5 and clamp.

    The weights were tuned against the 100-song US Pop benchmark cohort to give:

        - Lower valence (~0.40–0.50) for moody / low-groove ballads
        - Mid valence (~0.50–0.60) for neutral / mixed-emotion tracks
        - Higher valence (~0.60–0.75) for bright, groovy uptempo records

    This is deliberately simple and internally consistent rather than
    philosophically "correct".
    """
    energy = float(features_full.get("energy", 0.5) or 0.5)
    dance = float(features_full.get("danceability", 0.5) or 0.5)
    legacy_val = float(features_full.get("valence", 0.5) or 0.5)
    tempo = float(features_full.get("tempo_bpm", 112.0) or 112.0)
    mode = str(features_full.get("mode", "unknown")).lower()

    # Center around 0.5 so positive values are "brighter than neutral"
    energy_c = energy - 0.5
    dance_c = dance - 0.5
    legacy_c = legacy_val - 0.5

    # Tempo: treat ~112 BPM as neutral. Divide by 40 to keep |tempo_c| ~<= 1
    # for reasonable pop tempos.
    tempo_c = (tempo - 112.0) / 40.0

    # Mild major / minor bias. This is intentionally small; tempo/energy/dance
    # do most of the work.
    if mode == "major":
        mode_bias = 0.08
    elif mode == "minor":
        mode_bias = -0.08
    else:
        mode_bias = 0.0

    score = (
        0.25 * legacy_c +
        0.25 * energy_c +
        0.35 * dance_c +
        0.05 * tempo_c +
        mode_bias
    )

    # Map into [0,1] around 0.5. With K≈1.5 the 100-song benchmark cohort
    # lands roughly in 0.40–0.75.
    K = 1.5
    val = 0.5 + K * score
    return _clamp01(val)


def _band_from_thresholds(x: Optional[float], thresholds: Dict[str, float]) -> str:
    """
    Generic banding helper.

    thresholds: dict with 'lo', 'mid', 'hi' members (floats).
    """
    if x is None:
        return "unknown"
    try:
        xv = float(x)
    except Exception:
        return "unknown"

    lo = thresholds.get("lo", 0.33)
    mid = thresholds.get("mid", 0.66)

    if xv < lo:
        return "lo"
    if xv < mid:
        return "mid"
    return "hi"


# --------------------------------------------------------------------
# Axis computation
# --------------------------------------------------------------------

def compute_axes(features_full: Dict[str, Any], market_norms: Dict[str, Any]) -> List[float]:
    """
    Compute the 6 canonical audio axes used by HCI_v1/HCI_v2:

      0 TempoFit       – tempo vs. cohort norms (Gaussian around market mean)
      1 RuntimeFit     – runtime vs. cohort norms
      2 Energy         – normalized 0–1 energy envelope
      3 Danceability   – normalized 0–1 groove / movement
      4 Valence        – normalized 0–1 bright vs. dark emotional tone (local heuristic)
      5 LoudnessFit    – LUFS vs. target master loudness

    Notes on implementation:

    - TempoFit, RuntimeFit, LoudnessFit use a simple Gaussian fit around the
      market norms mean / std. If norms are missing, they fall back to 0.5.
    - Energy and Danceability are expected to already be in [0,1] from the
      feature extractor and are passed through with clamping.
    - Valence is *not* taken verbatim from features_full["valence"]. Instead
      we compute a local valence axis that blends:

        • legacy valence estimate (features_full["valence"])
        • energy (brighter / higher-energy arrangements → higher valence)
        • danceability (more movement → higher valence)
        • tempo (moderately faster than the ~112 BPM pop mean → slightly higher)
        • major/minor mode bias (major → small upward bias, minor → small downward)

      This is intentionally simple and fully transparent, designed to give a
      sensible spread across the 100-song benchmark cohort without pretending
      to be an oracle. Typical values for US Pop benchmarks land roughly in
      the 0.40–0.75 band.

    All returned axes are clipped to [0,1] and ordered as:

        [TempoFit, RuntimeFit, Energy, Danceability, Valence, LoudnessFit]
    """
    tempo = features_full.get("tempo_bpm")
    dur   = features_full.get("duration_sec")
    lufs  = features_full.get("loudness_LUFS")

    # Market norms can come either as a flat dict:
    #   {"tempo_mean", "tempo_std", "duration_mean", ...}
    # or nested under a MARKET_NORMS block with names like
    #   {"MARKET_NORMS": {
    #        "tempo_bpm_mean", "tempo_bpm_std",
    #        "runtime_sec_mean", "runtime_sec_std",
    #        "loudness_mean", "loudness_std",
    #    }}.
    #
    # We normalize both shapes into the local *_mu / *_sd variables.
    tempo_mu = market_norms.get("tempo_mean")
    tempo_sd = market_norms.get("tempo_std")
    dur_mu   = market_norms.get("duration_mean")
    dur_sd   = market_norms.get("duration_std")
    lufs_mu  = market_norms.get("loudness_mean")
    lufs_sd  = market_norms.get("loudness_std")

    nested_norms = market_norms.get("MARKET_NORMS")
    if isinstance(nested_norms, dict):
        if tempo_mu is None:
            tempo_mu = nested_norms.get("tempo_mean") or nested_norms.get("tempo_bpm_mean")
        if tempo_sd is None:
            tempo_sd = nested_norms.get("tempo_std") or nested_norms.get("tempo_bpm_std")
        if dur_mu is None:
            dur_mu = nested_norms.get("duration_mean") or nested_norms.get("runtime_sec_mean")
        if dur_sd is None:
            dur_sd = nested_norms.get("duration_std") or nested_norms.get("runtime_sec_std")
        if lufs_mu is None:
            lufs_mu = nested_norms.get("loudness_mean")
        if lufs_sd is None:
            lufs_sd = nested_norms.get("loudness_std")

    tempo_fit   = _gaussian_fit(tempo, tempo_mu, tempo_sd)
    runtime_fit = _gaussian_fit(dur,   dur_mu,   dur_sd)
    loud_fit    = _gaussian_fit(lufs,  lufs_mu,  lufs_sd)

    # Energy and Danceability are expected to be in [0,1]
    energy  = _clamp01(features_full.get("energy", 0.5))
    dance   = _clamp01(features_full.get("danceability", 0.5))

    # New: compute a local Valence axis from multiple audio features.
    valence_axis = _compute_valence_axis(features_full)

    return [
        float(tempo_fit),
        float(runtime_fit),
        float(energy),
        float(dance),
        float(valence_axis),
        float(loud_fit),
    ]


# --------------------------------------------------------------------
# Thresholds (these can be tuned or loaded externally)
# --------------------------------------------------------------------

# In this v1.1/v2-planning snapshot, thresholds are derived from the 100-song
# benchmark set and used for simple band labeling. They are *not* used to
# compute the continuous axis values directly; the continuous axes come from
# the raw numeric values.

TEMPO_THRESHOLDS = {
    "lo": 0.33,
    "mid": 0.66,
    "hi": 0.85,
}

RUNTIME_THRESHOLDS = {
    "lo": 0.33,
    "mid": 0.66,
    "hi": 0.85,
}

ENERGY_THRESHOLDS = {
    "lo": 0.33,
    "mid": 0.66,
    "hi": 0.85,
}

DANCE_THRESHOLDS = {
    "lo": 0.33,
    "mid": 0.66,
    "hi": 0.85,
}

VALENCE_THRESHOLDS = {
    "lo": 0.33,
    "mid": 0.66,
    "hi": 0.85,
}

LOUDNESS_THRESHOLDS = {
    "lo": 0.33,
    "mid": 0.66,
    "hi": 0.85,
}

# --------------------------------------------------------------------
# Human-facing band helpers (used in reports, not core scoring)
# --------------------------------------------------------------------

def band_tempo_fit(tf: Optional[float]) -> str:
    """
    Simple banding for TempoFit.
    """
    return _band_from_thresholds(tf, TEMPO_THRESHOLDS)


def band_runtime_fit(rf: Optional[float]) -> str:
    """
    Simple banding for RuntimeFit.
    """
    return _band_from_thresholds(rf, RUNTIME_THRESHOLDS)


def band_energy(energy: Optional[float]) -> str:
    """
    Canonical banding for Energy axis.
    Uses ENERGY_THRESHOLDS.
    """
    return _band_from_thresholds(energy, ENERGY_THRESHOLDS)


def band_danceability(dance: Optional[float]) -> str:
    """
    Canonical banding for Danceability axis.
    Uses DANCE_THRESHOLDS.
    """
    return _band_from_thresholds(dance, DANCE_THRESHOLDS)


def band_valence(valence: Optional[float]) -> str:
    """
    Canonical banding for Valence axis.
    Uses VALENCE_THRESHOLDS.
    """
    return _band_from_thresholds(valence, VALENCE_THRESHOLDS)


def band_loudness_fit(lf: Optional[float]) -> str:
    """
    Simple banding for LoudnessFit.
    """
    return _band_from_thresholds(lf, LOUDNESS_THRESHOLDS)


# --------------------------------------------------------------------
# CLI entry for debugging (optional)
# --------------------------------------------------------------------

def _load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def main() -> None:
    import argparse

    p = argparse.ArgumentParser(description="Compute 6 audio axes from features_full + market_norms.")
    p.add_argument("--features", type=str, required=True, help="Path to *.features.json")
    p.add_argument("--market-norms", type=str, required=False, default="", help="Optional market norms JSON")
    p.add_argument("--out", type=str, required=False, help="Optional output JSON (default: print to stdout)")
    args = p.parse_args()

    feat_path = Path(args.features)
    feats = _load_json(feat_path)
    if "features_full" in feats:
        feats = feats["features_full"]

    if args.market_norms:
        norms_path = Path(args.market_norms)
        norms = _load_json(norms_path)
    else:
        # Neutral-ish defaults if no norms file is provided.
        norms = {
            "tempo_mean": 120.0,
            "tempo_std":  20.0,
            "duration_mean": 200.0,
            "duration_std":  40.0,
            "loudness_mean": -10.0,
            "loudness_std":   3.0,
        }

    axes = compute_axes(feats, norms)
    out = {
        "axes": {
            "TempoFit": axes[0],
            "RuntimeFit": axes[1],
            "Energy": axes[2],
            "Danceability": axes[3],
            "Valence": axes[4],
            "LoudnessFit": axes[5],
        }
    }
    s = json.dumps(out, indent=2)
    if args.out:
        Path(args.out).write_text(s)
    else:
        print(s)


if __name__ == "__main__":
    main()
