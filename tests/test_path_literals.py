from pathlib import Path

FORBIDDEN_SUBSTRINGS = ("calibration/", "data/")
# Legacy scripts still carrying literals; shrink over time. Spine tools are skipped by directory rule below.
ALLOWLIST = {
    "tools/hci/historical_echo_runner.py",
    "tools/task_conductor/echo_broker.py",
    "shared/content_addressed_broker/broker.py",
    "infra/scripts/data_bootstrap.py",
    "tools/hci_recompute_axes_for_root.py",
    "tools/hci_v2_build_training_matrix.py",
    "tools/spotify_apply_overrides_to_core_corpus.py",
    "tools/ma_fit_hci_calibration_from_hitlist.py",
    "tools/calibrate_hci.py",
    "tools/hci_fit_hci_to_et.py",
    "tools/hci_compare_targets.py",
    "tools/spotify_backfill_metadata_from_ids.py",
    "tools/hci_v2_build_targets.py",
    "tools/spotify_enrich_core_corpus.py",
    "tools/hci_v2_eval_training.py",
    "tools/hci_audio_v2_backfill.py",
    "tools/ma_benchmark_check_ml.py",
    "tools/fit_loudness_norms_from_local_features.py",
    "tools/ma_truth_vs_ml_sanity.py",
    "tools/ma_truth_vs_ml_export_buckets.py",
    "tools/hci_v2_train_model.py",
    "tools/calib_coverage.py",
    "tools/ma_aee_ml_apply.py",
    "tools/ma_benchmark_check.py",
    "tools/loudness_report.py",
    "tools/hci_audio_v2_fit_calibration_from_db.py",
    "tools/ma_truth_vs_ml_add_review_columns.py",
    "tools/ma_truth_vs_ml_report.py",
    "tools/make_calibration_snapshot.py",
    "tools/hci_audio_v2_apply_calibration.py",
    "tools/debug_spotify_drift.py",
    "tools/ma_calibrate.py",
    "tools/hci_audio_v2_fit.py",
    "tools/hci_axes_diagnostics.py",
    "tools/ma_apply_axis_bands_from_thresholds.py",
    "tools/ma_aee_ml_train.py",
    "tools/fetch_spotify_features.py",
    "tools/debug_spotify_drift_1985_1986.py",
    "tools/calibration_validator.py",
    "tools/spotify_retry_unmatched_core_spine.py",
    "tools/build_offline_spotify_features.py",
    "tools/calibration_runner.py",
    "tools/hci_v2_axes_diagnostics.py",
    "tools/hci_v2_apply.py",
    "tools/ma_hci_from_features.py",
    "tools/aee_band_thresholds.py",
    "tools/hci_echo_probe_from_spine_v1.py",
    "tools/ma_simple_hci_from_features.py",
    "tools/ma_band_thresholds_from_csv.py",
    "tools/hci_audio_v2_apply.py",
    "tools/lyrics/import_kaylin_lyrics_into_db_v1.py",
    "engines/lyrics_engine/tools/lyrics/import_kaylin_lyrics_into_db_v1.py",
    "tools/audio/build_historical_echo_corpus.py",
    "tools/audio/historical_echo_db_import.py",
    "tools/audio/historical_echo_core_spine_import.py",
    "tools/audio/sanitize_filenames.py",
    "tools/audio/historical_echo_backfill_tier3_audio.py",
    "tools/audio/historical_echo_stats.py",
    "tools/audio/spine/build_spine_master_tier2_modern_lanes_v1.py",
    "tools/audio/spine/build_spine_master_tier3_modern_lanes_v1.py",
    "tools/audio/spine/build_yearend_top200_from_weekly_hot100.py",
    "tools/audio/spine/build_yearend_hot100_top100_from_weekly_v1.py",
    "tools/audio/spine/build_spine_audio_from_tonyrwen_tier2_modern_v1.py",
    "tools/audio/spine/build_spine_audio_from_hot100_lyrics_audio_v1.py",
    "tools/audio/spine/enrich_spine_with_lanes_v1.py",
    "tools/audio/spine/report_spine_missing_audio_v1.py",
    "tools/audio/spine/scan_external_datasets_v1.py",
    "tools/audio/spine/build_spine_audio_from_elpsyk_tier1_sandbox_v1.py",
    "tools/audio/spine/build_spine_success_from_ut_hot100_v1.py",
    "tools/audio/spine/import_spine_master_lanes_into_db_v1.py",
    "tools/audio/spine/build_spine_audio_from_hot100songs_v1.py",
    "tools/audio/spine/build_spine_audio_from_patrick_v1.py",
    "tools/audio/spine/build_spine_master_tier2_modern_v1.py",
    # Legacy audio spine toolchain scanned separately; excluded below.
    "tools/calibration_readiness.py",
    "tools/audio/spine/prepare_spotify_queries_for_missing_v1.py",
    "tools/external/acousticbrainz_fetch_for_spine_mbids.py",
    "tools/external/acousticbrainz_diagnostics_tier3.py",
    # Known legacy literals (market norms/billboard/ttc tooling + host stub); trim as refactors land.
    "tools/market_norms_db_report.py",
    "tools/market_norms_ut_billboard_sync.py",
    "engines/recommendation_engine/recommendation_engine/market_norms/__init__.py",
    "hosts/advisor_host/cli/http_stub.py",
    # Shared shims (intentional mirrors)
    "shared/config/__init__.py",
    "shared/config/paths.py",
    "shared/config/audio.py",
    "shared/config/constants.py",
    "shared/config/neighbors.py",
    "shared/config/pipeline.py",
    "shared/config/profiles.py",
    "shared/config/scripts.py",
    "shared/security/__init__.py",
    "shared/security/config.py",
    "shared/security/db.py",
    "shared/security/files.py",
    "shared/security/paths.py",
    "shared/security/subprocess.py",
}


def test_no_hardcoded_paths_outside_ma_config():
    """
    Heuristic: flag new hard-coded calibration/data paths outside ma_config/shared, docs, tests.
    See docs/config_paths.md for the contract and how to add new path helpers.
    """
    repo = Path(__file__).resolve().parent.parent
    violations = []
    for path in repo.rglob("*.py"):
        # Skip caches, ma_config (canonical), tests, docs build helpers
        if "ma_config" in path.parts or "tests" in path.parts or "site-packages" in path.parts:
            continue
        if path.match("**/__pycache__/**"):
            continue
        rel = str(path.relative_to(repo))
        if rel in ALLOWLIST:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for sub in FORBIDDEN_SUBSTRINGS:
            if sub in text:
                violations.append(rel)
                break
    assert not violations, f"Hard-coded path substrings found in: {violations}"
