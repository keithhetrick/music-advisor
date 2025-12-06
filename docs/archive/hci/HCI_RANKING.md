# HCI_v1 Ranking Cheat

Rank HCI_v1 scores within a folder of `.hci.json` files.

## Command

```bash
python tools/hci_rank_from_folder.py \
  --root features_output/2025/11/25 \
  --out /tmp/hci_rank_summary.txt \
  --csv-out /tmp/hci_rank.csv \
  --markdown-out /tmp/hci_rank.md
```

- Default text output: `<root>/hci_rank_summary.txt` (if `--out` not provided).
- `--tiers WIP-A+,WIP-A` to filter tiers (default: all).
- Includes stats (max/min/median) and tier counts.
- Two tables: compact score+title, then full detail (score, raw, tier, title).
- CSV/Markdown outputs are optional.

Legend/Notes:

- `score` = `HCI_v1_final_score` (audio-based historical echo; higher = closer to long-run US Pop archetypes).
- `tier` = qualitative label from `.hci.json` (WIP-A+/A/B/C).
- `raw` = uncalibrated score (if present).
- HCI_v1 is not a hit predictor; it is an audio historical-echo diagnostic.
