#!/usr/bin/env python3
"""
Lightweight lyric sectionizer
- Detects CHORUS by line repetition and n-gram overlap
- Fallbacks to VERSE/BRIDGE heuristics
Safe to use as a library from lyricflow.py or elsewhere.
"""
from collections import Counter
import re
from typing import List, Dict, Optional

TOKEN_RE = re.compile(r"[A-Za-z0-9']+")

def tokenize(line: str) -> List[str]:
    return TOKEN_RE.findall(line.lower())

def jaccard(a: List[str], b: List[str]) -> float:
    sa, sb = set(a), set(b)
    if not sa or not sb: return 0.0
    return len(sa & sb) / len(sa | sb)

def ngram_tokens(tokens: List[str], n: int = 2) -> List[str]:
    return [" ".join(tokens[i:i+n]) for i in range(max(0, len(tokens)-n+1))]

def chorus_candidates(lines: List[str], top_k: int = 3) -> List[str]:
    """
    Return top repeated lines (or near-duplicates) as chorus candidates.
    """
    # exact repeats first
    counts = Counter([l.strip().lower() for l in lines if l.strip()])
    candidates = [t for t, c in counts.most_common() if c >= 2]

    # near-duplicate booster via bigrams overlap
    if len(candidates) < top_k:
        bigram_map = {}
        for l in lines:
            toks = tokenize(l)
            bigrams = ngram_tokens(toks, 2)
            bigram_map[l] = Counter(bigrams)
        scored = []
        for i, li in enumerate(lines):
            for j, lj in enumerate(lines):
                if i >= j: continue
                if not li.strip() or not lj.strip(): continue
                a, b = bigram_map[li], bigram_map[lj]
                common = sum((a & b).values())
                total = sum((a | b).values()) or 1
                sim = common / total
                if sim >= 0.5:
                    scored.append(li.strip().lower())
                    scored.append(lj.strip().lower())
        if scored:
            c2 = Counter(scored)
            for t, _ in c2.most_common():
                if t not in candidates:
                    candidates.append(t)
                if len(candidates) >= top_k:
                    break

    return candidates[:top_k]

def assign_sections(raw_lines: List[str]) -> List[Dict]:
    """
    Very light sectionizer:
    - Groups lines into blocks separated by blank lines
    - Tries to label one block as CHORUS based on repetition across blocks
    - Others default to VERSE; single-liners after chorus may be POST
    """
    # split into blocks
    blocks = []
    buf = []
    for line in raw_lines:
        if line.strip() == "":
            if buf: blocks.append(buf); buf=[]
        else:
            buf.append(line)
    if buf: blocks.append(buf)

    all_lines = [l for b in blocks for l in b]
    chorus_lines = set(chorus_candidates(all_lines, top_k=3))

    labeled = []
    chorus_found = False
    for b in blocks:
        block_text = " ".join([l.strip().lower() for l in b])
        # If any line in this block is a candidate → chorus
        is_chorus = any(l.strip().lower() in chorus_lines for l in b)
        if is_chorus and not chorus_found:
            tag = "CHORUS"
            chorus_found = True
        else:
            tag = "VERSE"

        labeled.append({
            "tag": tag,
            "lines": b
        })

    # post-chorus heuristic: single short line after chorus
    for i in range(1, len(labeled)):
        prev_is_chorus = labeled[i-1]["tag"] == "CHORUS"
        if prev_is_chorus and len(labeled[i]["lines"]) <= 2:
            labeled[i]["tag"] = "POST"

    return labeled

def sectionize_text(text: str) -> List[Dict]:
    """
    Accepts a raw lyric string; returns sections list.
    """
    raw_lines = text.splitlines()
    return assign_sections(raw_lines)
