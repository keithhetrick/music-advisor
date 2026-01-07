"""Compatibility shim delegating to shared.ma_utils.schema_utils."""
from shared.ma_utils.schema_utils import (
    lint_features_payload,
    lint_hci_payload,
    lint_json_file,
    lint_merged_payload,
    lint_neighbors_payload,
    lint_pack_payload,
    lint_run_summary,
    validate_with_schema,
)

__all__ = [
    "lint_features_payload",
    "lint_hci_payload",
    "lint_json_file",
    "lint_merged_payload",
    "lint_neighbors_payload",
    "lint_pack_payload",
    "lint_run_summary",
    "validate_with_schema",
]
