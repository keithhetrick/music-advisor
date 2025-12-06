# ... same imports as lyricflow, plus:
from text_sim import fuzzy_ratio, best_match
# (optional) semantic: from sentence_transformers import SentenceTransformer, util

def mine_hook_phrase(lines: list[str], short_line_max=7, min_ratio=78):
    # 1) pool short lines + line tails as candidates
    cands = []
    for ln in lines:
        toks = [t for t in re.findall(r"[a-z0-9']+", ln.lower()) if t]
        if not toks: continue
        if len(toks) <= short_line_max:
            cands.append(" ".join(toks))
        if len(toks) >= 3:
            tail = " ".join(toks[-min(6, len(toks)):])
            cands.append(tail)
    cands = list(dict.fromkeys(cands))  # dedupe

    # 2) cluster via fuzzy threshold
    best_phrase, best_score = None, 0.0
    for i, q in enumerate(cands):
        # fast approximate: compare to a subset or all (N small)
        scores = [fuzzy_ratio(q, c) for c in cands if c != q]
        sim_hits = [s for s in scores if s >= min_ratio]
        if len(sim_hits) >= 1:
            score = (len(sim_hits)+1) * (sum(sim_hits)/max(1,len(sim_hits)))
            if score > best_score:
                best_phrase, best_score = q, score
    return best_phrase  # may be None

def hook_density_fuzzy(block_lines: list[str], hook: str, min_ratio=78) -> float:
    if not hook or not block_lines: return 0.0
    hits = 0
    for ln in block_lines:
        if fuzzy_ratio(hook, ln) >= min_ratio:
            hits += 1
    return hits / max(1, len(block_lines))

def chorus_scores_plus(blocks, hook, energies, weights, min_ratio=78, repeat_bonus=0.05):
    scores, tags = [], []
    prev_e = None
    # repetition proxy = number of blocks whose density_fuzzy >= 0.5
    densities = []
    for b in blocks:
        d = hook_density_fuzzy([x["text"] for x in b], hook, min_ratio=min_ratio)
        densities.append(d)
    repetition_global = sum(1 for d in densities if d >= 0.5)
    for i, b in enumerate(blocks):
        d = densities[i]
        e = energies[i] if i < len(energies) else None
        lift = max(0.0, min(1.0, (e - prev_e))) if (e is not None and prev_e is not None) else 0.0
        prev_e = e if e is not None else prev_e
        rep = repeat_bonus if repetition_global >= 2 and d >= 0.3 else 0.0
        score = weights["fuzzy"]*d + weights["energy"]*lift + weights["repeat"]*rep
        scores.append(float(max(0.0, min(1.0, score))))
    tags = ["CHORUS" if s >= 0.58 and densities[i] >= 0.3 else "VERSE" for i, s in enumerate(scores)]
    return scores, tags
