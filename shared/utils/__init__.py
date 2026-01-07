"""
Shared utility namespace.

Currently re-exports helpers from `shared.core` and path helpers from
`shared.config.paths` to provide a single utilities home. Extend with additional
helpers over time; keep imports stable for downstream callers.
"""

from shared.core import (
    DEFAULT_LCI_PROFILE,
    DEFAULT_LCI_CALIBRATION_PATH,
    DEFAULT_TTC_PROFILE,
    DEFAULT_TTC_CONFIG_PATH,
    resolve_profile_config,
)
from shared.utils.paths import (
    get_repo_root,
    get_data_root,
    get_calibration_root,
    get_features_output_root,
    get_private_root,
    get_local_assets_root,
    get_spine_root,
    get_spine_backfill_root,
    get_spine_master_csv,
    get_lyric_intel_db_path,
    get_historical_echo_db_path,
    get_hci_v2_targets_csv,
    get_hci_v2_corpus_csv,
    get_hci_v2_training_csv,
    get_hci_v2_training_eval_csv,
    get_hci_v2_overlap_csv,
    get_hci_v2_audio_seed_csv,
    get_audio_hci_v2_model_path,
    get_audio_hci_v2_model_meta_path,
    get_audio_hci_v2_calibration_path,
    get_core_spine_root,
    get_yearend_hot100_root,
    get_yearend_hot100_top100_path,
    get_yearend_hot100_top200_path,
)

__all__ = [
    # core
    "DEFAULT_LCI_PROFILE",
    "DEFAULT_LCI_CALIBRATION_PATH",
    "DEFAULT_TTC_PROFILE",
    "DEFAULT_TTC_CONFIG_PATH",
    "resolve_profile_config",
    # paths
    "get_repo_root",
    "get_data_root",
    "get_calibration_root",
    "get_features_output_root",
    "get_private_root",
    "get_local_assets_root",
    "get_spine_root",
    "get_spine_backfill_root",
    "get_spine_master_csv",
    "get_lyric_intel_db_path",
    "get_historical_echo_db_path",
    "get_hci_v2_targets_csv",
    "get_hci_v2_corpus_csv",
    "get_hci_v2_training_csv",
    "get_hci_v2_training_eval_csv",
    "get_hci_v2_overlap_csv",
    "get_hci_v2_audio_seed_csv",
    "get_audio_hci_v2_model_path",
    "get_audio_hci_v2_model_meta_path",
    "get_audio_hci_v2_calibration_path",
    "get_core_spine_root",
    "get_yearend_hot100_root",
    "get_yearend_hot100_top100_path",
    "get_yearend_hot100_top200_path",
]
