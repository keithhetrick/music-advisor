#!/usr/bin/env python3
from __future__ import annotations

"""
hci_add_philosophy_block.py

Post-process *.client.rich.txt files and append (or replace) a canonical
HCI_v1 philosophy block so that every pack clearly explains:

  - HCI_v1 is a historical-echo audio metric.
  - It is NOT a hit predictor.
  - The Blinding Lights WIP trap example.

This script is intentionally separate from ma_merge_client_and_hci.py so we
don't risk breaking your existing client pack format. You can simply add
this as the final step in your Automator workflows.
"""

import argparse
from pathlib import Path
from typing import List

# Marker line that identifies the auto-managed block.
PHILOSOPHY_MARKER = "[HCI_v1_PHILOSOPHY_BLOCK]"

# Canonical text we want to inject into every .client.rich.txt
# You can edit the copy here; the marker MUST stay the same if you
# want replace-mode to work later.
PHILOSOPHY_BLOCK = f"""
{PHILOSOPHY_MARKER}
### What the HCI_v1 audio score means

> **HCI_v1 is a historical-echo audio score, not a hit predictor.**  
> It measures how this audio file’s features align with long-running US Pop hit archetypes and ignores marketing, artist fame, and virality. A strong score means the **audio DNA is living in a proven zone**, not that the song is guaranteed to be a hit.

HCI_v1 looks only at the audio file you give it — tempo, runtime, loudness, energy, danceability, valence, and other derived features — and estimates how strongly that file participates in long-running, empirically successful US Pop **hit archetypes**.

It does **not** know:

- How many streams the song has.
- Who the artist is.
- How big the marketing push is.
- Whether it has gone viral on TikTok, radio, or anywhere else.

Because of that, a structurally strong WIP mix can sometimes score higher than a rough, alternate, or mis-aligned version of a legendary hit. This is expected and healthy behavior.

**Sanity check example (Blinding Lights trap):**

Music Advisor intentionally keeps a WIP copy of **“Blinding Lights”** in the WIP folder as a trap/check.  
That audio currently scores around **0.66** on this metric — even though the real song is the most-streamed track of all time. This is expected:

- HCI_v1 is scoring the **audio-only historical echo** of the file you fed it.
- It is *not* measuring real-world success, cultural impact, or marketing.

**Bottom line:**  
Use HCI_v1 as a **diagnostic tool for audio shape and historical echo** — to pressure-test tempo, loudness, runtime, energy, and related axes against proven archetypes. It is designed to support your judgment, not to replace your ear, your team, or the market.
""".lstrip(
    "\n"
)


def find_rich_files(roots: List[Path]) -> List[Path]:
    out: List[Path] = []
    for root in roots:
        if not root.exists():
            print(f"[WARN] Root does not exist; skipping: {root}")
            continue
        for path in root.rglob("*.client.rich.txt"):
            out.append(path)
    return sorted(out)


def apply_block_to_text(text: str, mode: str) -> str:
    """
    Insert or replace the philosophy block in a single .client.rich.txt.

    Modes:
      - append:  if marker is present, leave file unchanged;
                 otherwise append the block to the end.
      - replace: if marker is present, replace from marker to EOF
                 with the canonical block; if not present, append.
    """
    if PHILOSOPHY_MARKER not in text:
        # No existing marker: just append.
        if not text.strip():
            # Empty file: just return the block.
            return PHILOSOPHY_BLOCK + "\n"
        return text.rstrip() + "\n\n" + PHILOSOPHY_BLOCK + "\n"

    if mode == "append":
        # Marker already present, and append mode = do nothing.
        return text

    # replace mode: replace from marker to end.
    idx = text.index(PHILOSOPHY_MARKER)
    prefix = text[:idx].rstrip()
    return prefix + "\n\n" + PHILOSOPHY_BLOCK + "\n"


def main() -> None:
    ap = argparse.ArgumentParser(
        description=(
            "Append or replace a canonical HCI_v1 philosophy block in all "
            "*.client.rich.txt files under the given root(s)."
        )
    )
    ap.add_argument(
        "--root",
        action="append",
        required=True,
        help="Root directory containing *.client.rich.txt files (can be given multiple times).",
    )
    ap.add_argument(
        "--mode",
        choices=["append", "replace"],
        default="append",
        help=(
            "How to handle existing blocks. 'append' (default) leaves files "
            "unchanged if the marker already exists. 'replace' overwrites any "
            "existing block (from marker to EOF) with the canonical text."
        ),
    )
    args = ap.parse_args()

    roots = [Path(r).expanduser().resolve() for r in args.root]
    print(
        f"[INFO] Adding HCI philosophy block in mode={args.mode} for roots: "
        + ", ".join(str(r) for r in roots)
    )

    files = find_rich_files(roots)
    print(f"[INFO] Found {len(files)} *.client.rich.txt file(s).")

    updated = 0
    skipped = 0

    for path in files:
        try:
            text = path.read_text(encoding="utf-8")
        except Exception as exc:
            print(f"[WARN] Could not read {path}: {exc}")
            skipped += 1
            continue

        new_text = apply_block_to_text(text, mode=args.mode)

        if new_text == text:
            skipped += 1
            continue

        try:
            tmp = path.with_suffix(path.suffix + ".tmp")
            tmp.write_text(new_text, encoding="utf-8")
            tmp.replace(path)
            updated += 1
        except Exception as exc:
            print(f"[WARN] Could not write {path}: {exc}")
            skipped += 1

    print(f"[DONE] Updated {updated} file(s); skipped {skipped}.")


if __name__ == "__main__":
    main()
