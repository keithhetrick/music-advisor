#!/usr/bin/env python3
# lyricflow.py — ASR + dual segmentation + fuzzy-lite hook detection + tempo-aware windows
import argparse, json, time, pathlib, re, difflib
from typing import List, Dict, Tuple, Optional
import numpy as np

# Optional audio energy cue (graceful fallback if librosa missing)
try:
    import librosa
except Exception:
    librosa = None

from faster_whisper import WhisperModel

# ---------------- text utils ----------------
STOP = set("""
a an the and or but if then so cuz cause 's 're i'm you're he's she's it's we're they're
i you he she it we they me my mine your yours his her hers its our ours their theirs
to for of in on at by with from as is are was were be been being do does did will would
""".split())

def norm(s: str) -> str:
    s = s.lower().strip()
    s = re.sub(r"[^a-z0-9'\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def toks(s: str) -> List[str]:
    return [t for t in re.findall(r"[a-z0-9']+", s.lower()) if t and t not in STOP]

def ngrams(seq: List[str], n: int) -> List[Tuple[str,...]]:
    return [tuple(seq[i:i+n]) for i in range(max(0, len(seq)-n+1))]

# ---------------- ASR ----------------
def asr_segments(audio_path: str, model_size: str="base") -> Tuple[List[Dict], float, float]:
    model = WhisperModel(model_size, compute_type="int8")
    segments, info = model.transcribe(audio_path, beam_size=5)
    seq = []; dur = 0.0; probs = []
    for s in segments:
        txt = (s.text or "").strip()
        if not txt: continue
        start = float(getattr(s, "start", 0.0) or 0.0)
        end   = float(getattr(s, "end", 0.0) or 0.0)
        dur = max(dur, end)
        seq.append({"text": txt, "start": start, "end": end})
        if getattr(s, "avg_logprob", None) is not None:
            probs.append(max(0.0, min(1.0, 1.0 + float(s.avg_logprob))))
    asr_conf = round(sum(probs)/len(probs), 2) if probs else 0.7
    return seq, dur, asr_conf

# ---------------- segmentation ----------------
def split_blocks_by_gap(seg: List[Dict], gap_sec: float=3.0) -> List[List[Dict]]:
    if not seg: return []
    blocks = []; buf = [seg[0]]
    for prev, cur in zip(seg, seg[1:]):
        if cur["start"] - prev["end"] >= gap_sec:
            blocks.append(buf); buf = [cur]
        else:
            buf.append(cur)
    blocks.append(buf)
    return blocks

def choose_tempo_window_sec(tempo_bpm: Optional[float], duration_sec: float) -> float:
    """
    Choose a musical window in seconds using 4/4 bars:
      - prefer 8 bars for songs <= 4 min, 16 bars for longer
      - clamp window to [8s, 24s] so it stays useful for detection
    """
    if not tempo_bpm or tempo_bpm <= 0:
        return 12.0
    bars = 8 if duration_sec <= 240 else 16
    beats_per_bar = 4
    sec_per_beat = 60.0 / float(tempo_bpm)
    window_sec = bars * beats_per_bar * sec_per_beat
    return float(np.clip(window_sec, 8.0, 24.0))

def split_blocks_fixed(seg: List[Dict], window_sec: float) -> List[List[Dict]]:
    """Fallback: split by fixed/tempo-aware windows so we always get multi-block structure."""
    if not seg: return []
    start_all = seg[0]["start"]; end_all = seg[-1]["end"]
    if end_all <= start_all:  # guard
        return [seg]
    cuts = np.arange(start_all + window_sec, end_all, window_sec)
    blocks = []; buf = []; cut_i = 0
    next_cut = cuts[cut_i] if cut_i < len(cuts) else float("inf")
    for s in seg:
        buf.append(s)
        while s["end"] >= next_cut:
            if buf:
                blocks.append(buf)
            buf=[]
            cut_i += 1
            next_cut = cuts[cut_i] if cut_i < len(cuts) else float("inf")
    if buf: blocks.append(buf)
    return [b for b in blocks if b]

def lines_from_block(block: List[Dict]) -> List[str]:
    return [x["text"] for x in block]

def block_window(block: List[Dict]) -> Tuple[float,float]:
    return float(block[0]["start"]), float(block[-1]["end"])

# ---------------- audio energy per block (optional) ----------------
def block_energy_profile(audio_path: str, blocks: List[List[Dict]]) -> List[Optional[float]]:
    if librosa is None or not blocks:
        return [None]*len(blocks)
    try:
        y, sr = librosa.load(audio_path, sr=44100, mono=True)
        rms = librosa.feature.rms(y=y, frame_length=2048, hop_length=512).flatten()
        if len(rms) == 0 or np.max(rms) <= 0: return [None]*len(blocks)
        times = np.arange(len(rms)) * (512.0 / 44100.0)
        out = []
        for b in blocks:
            start, end = block_window(b)
            mask = (times >= start) & (times <= end)
            vals = rms[mask]
            med = float(np.median(vals)) if vals.size else None
            out.append(med)
        valid = [v for v in out if v is not None]
        if not valid: return [None]*len(out)
        vmin, vmax = min(valid), max(valid)
        if vmax - vmin < 1e-9: return [0.5 if v is not None else None for v in out]
        return [float((v - vmin)/(vmax - vmin)) if v is not None else None for v in out]
    except Exception:
        return [None]*len(blocks)

# ---------------- hook mining (fuzzy-lite, no new deps) ----------------
def top_hook_phrase(lines: List[str]) -> Optional[str]:
    """Pick a repeated 3–5 word phrase using token tails frequency."""
    tails = []
    for ln in lines:
        t = toks(ln)
        for n in (3,4,5):
            if len(t) >= n:
                tails.append(" ".join(t[-n:]))
    if not tails: return None
    counts = {}
    for tail in tails:
        counts[tail] = counts.get(tail, 0) + 1
    best, c = max(counts.items(), key=lambda kv: kv[1])
    if c < 2:
        return None
    return best

def fuzzy_like(a: str, b: str) -> float:
    """0..1 similarity using difflib + token Jaccard (no external deps)."""
    a_n, b_n = norm(a), norm(b)
    r1 = difflib.SequenceMatcher(None, a_n, b_n).ratio()  # chars
    ta, tb = set(toks(a_n)), set(toks(b_n))
    j = len(ta & tb) / max(1, len(ta | tb))               # Jaccard
    return 0.6*r1 + 0.4*j

def hook_density_fuzzy(block_lines: List[str], hook: str, thr: float=0.72) -> float:
    if not hook or not block_lines: return 0.0
    hits = sum(1 for ln in block_lines if fuzzy_like(hook, ln) >= thr)
    return hits / max(1, len(block_lines))

def earliest_hook_time(segs: List[Dict], hook: Optional[str], thr: float=0.72) -> Optional[float]:
    if not hook: return None
    for s in segs:
        if fuzzy_like(hook, s["text"]) >= thr:
            return round(float(s["start"]), 2)
    return None

# ---------------- scoring + labeling ----------------
def chorus_scores(blocks: List[List[Dict]], hook: Optional[str], energies: List[Optional[float]], thr: float=0.72):
    """Return (scores[0..1], tags). score = 0.6*density + 0.4*energy_lift (if energy available)."""
    scores = []; tags = []; prev_e = None
    densities = [hook_density_fuzzy(lines_from_block(b), hook, thr) for b in blocks]
    for i, b in enumerate(blocks):
        e = energies[i] if i < len(energies) else None
        lift = 0.0
        if e is not None and prev_e is not None:
            lift = max(0.0, min(1.0, e - prev_e))
        prev_e = e if e is not None else prev_e
        score = densities[i] if (e is None or prev_e is None) else (0.6*densities[i] + 0.4*lift)
        score = float(np.clip(score, 0.0, 1.0))
        scores.append(score)
        tags.append("CHORUS" if (score >= 0.50 and densities[i] >= 0.30) else "VERSE")
    return scores, tags, densities

# ---------------- main ----------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--audio", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--enable-asr", default="1", choices=["0","1"])
    ap.add_argument("--model", default="base")
    ap.add_argument("--tempo-bpm", type=float, default=None)   # NEW: tempo-aware windows
    args = ap.parse_args()

    provenance = {
        "lyrics_source": "none",
        "source_chain": [],
        "lang": "en",
        "confidence_overall": 0.0,
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }

    text_sections = None
    section_timestamps = None
    derived = {"hook_repeats": 0, "hook_first_exposure_sec": None, "chorus_confidence": None}

    if args.enable_asr == "1":
        segs, duration, asr_conf = asr_segments(args.audio, args.model)
        provenance["source_chain"].append(f"asr/faster-whisper:{args.model}")

        if segs:
            # Primary: time-gap segmentation
            blocks = split_blocks_by_gap(segs, gap_sec=3.0)
            # Fallback: if only one block, use tempo-aware windows
            if len(blocks) == 1:
                window_sec = choose_tempo_window_sec(args.tempo_bpm, duration)
                blocks = split_blocks_fixed(segs, window_sec=window_sec)

            # Hook mining from all lines
            all_lines = [s["text"] for s in segs]
            hook = top_hook_phrase(all_lines)

            # Per-block energy (optional)
            energies = block_energy_profile(args.audio, blocks)

            # Block scoring + labels (fuzzy-lite)
            scores, tags, densities = chorus_scores(blocks, hook, energies, thr=0.72)

            # Build sections + stamps
            sections, stamps, chorus_idx = [], [], []
            for i, b in enumerate(blocks):
                start, end = block_window(b)
                tag = tags[i]
                if tag == "CHORUS": chorus_idx.append(i)
                sections.append({"tag": tag, "lines": lines_from_block(b)})
                stamps.append({"tag": tag, "start_sec": round(start,2), "end_sec": round(end,2)})

            # TTC/exposures from matches across ALL segments
            ttc = earliest_hook_time(segs, hook, thr=0.72)
            exposures = 0
            if hook:
                exposures = sum(1 for s in segs if fuzzy_like(hook, s["text"]) >= 0.72)

            chorus_conf = round(float(np.mean([scores[i] for i in chorus_idx])) , 2) if chorus_idx else None

            text_sections = sections
            section_timestamps = stamps
            derived = {
                "hook_repeats": int(exposures),
                "hook_first_exposure_sec": ttc,
                "chorus_confidence": chorus_conf
            }

            provenance["lyrics_source"] = "asr"
            provenance["confidence_overall"] = float(np.clip(0.5*asr_conf + 0.5*(chorus_conf or 0.0), 0.0, 1.0)) if chorus_conf is not None else asr_conf

    payload = {
        "provenance": provenance,
        "text": {"sections": text_sections} if text_sections else None,
        "features_only": None,
        "section_timestamps": section_timestamps,
        "derived": derived
    }
    pathlib.Path(args.out).write_text(json.dumps(payload, indent=2))
    print(f"[lyricflow] wrote {args.out} ({'asr' if text_sections else 'no-lyrics'})")

if __name__ == "__main__":
    main()
