from rapidfuzz import fuzz, process

def fuzzy_ratio(a: str, b: str) -> int:
    # token_set_ratio handles reorderings/dupes better for choruses
    return fuzz.token_set_ratio(a, b)  # 0..100

def best_match(query: str, candidates: list[str]) -> int:
    # returns top score vs list
    if not candidates: return 0
    return max(fuzzy_ratio(query, c) for c in candidates)
