# Global policy knobs for how cohort baselines influence scoring (ma_audio_engine).

# Global policy knobs for how cohort baselines influence scoring.
BASELINE_INFLUENCE = {
    "normalize_features": True,     # use cohort μ/σ to produce z-features
    "market_prior_weight": 0.10,    # 0..1; tiny weight for market-fit prior
    "max_prior_delta": 0.03,        # clamp total market-axis nudge ±0.03
    "affects_caps": False,          # baseline NEVER changes caps/gates
}
