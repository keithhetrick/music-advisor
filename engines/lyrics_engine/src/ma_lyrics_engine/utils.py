"""
Shared lyric engine utilities and constants.
"""
from __future__ import annotations

import hashlib
import re
import unicodedata
from collections import defaultdict
from typing import Dict

SECTION_ALIASES: Dict[str, str] = {
    "VERSE": "VERSE",
    "V": "VERSE",
    "INTRO": "INTRO",
    "IN": "INTRO",
    "CHORUS": "CHORUS",
    "HOOK": "CHORUS",
    "C": "CHORUS",
    "PRE": "PRE",
    "PRE-CHORUS": "PRE",
    "POST": "POST",
    "BRIDGE": "BRIDGE",
    "BRK": "BRIDGE",
    "OUTRO": "OUTRO",
    "OUT": "OUTRO",
}

PROFANITY = {
    "fuck",
    "shit",
    "bitch",
    "damn",
    "ass",
    "bastard",
    "crap",
    "dick",
    "piss",
}

PRONOUNS_1P = {"i", "me", "my", "mine", "we", "us", "our", "ours"}
PRONOUNS_2P = {"you", "your", "yours", "yall", "ya"}
PRONOUNS_3P = {"he", "she", "they", "them", "his", "her", "hers", "their", "theirs"}

THEME_LEXICON = {
    "love": {"love", "heart", "together", "kiss", "darling", "baby"},
    "heartbreak": {"lonely", "apart", "goodbye", "cry", "tears", "miss"},
    "empowerment": {"strong", "rise", "power", "fight", "win", "stand"},
    "nostalgia": {"remember", "memories", "yesterday", "back", "old", "home", "photo", "album", "kitchen"},
    "flex": {"money", "gold", "flex", "rolls", "chain", "ice"},
    "spiritual": {"god", "pray", "faith", "heaven", "angel", "bless"},
    "family": {
        "mother",
        "father",
        "sister",
        "brother",
        "family",
        "home",
        "grandma",
        "grandmother",
        "granny",
        "nana",
        "papa",
        "grandpa",
        "grandfather",
        "grandkids",
        "grandchildren",
        "porch",
        "kitchen",
        "table",
        "hospital",
        "nurse",
        "bedside",
    },
    "small_town": {"town", "road", "truck", "porch", "county", "river"},
}


def normalize_text(s: str) -> str:
    """Lowercase, strip accents/punctuation, collapse whitespace."""
    if s is None:
        return ""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = s.lower()
    s = s.replace("&", " and ")
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def slugify_song(title: str, artist: str, year: int | None) -> str:
    base = f"{normalize_text(title)}___{normalize_text(artist)}___{year or 'unk'}"
    digest = hashlib.sha1(base.encode("utf-8")).hexdigest()[:8]
    return f"{base}___{digest}"


def clean_lyrics_text(raw: str) -> str:
    if raw is None:
        return ""
    text = raw.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\u00a0", " ")
    text = re.sub(r"\t", " ", text)
    text = re.sub(r"\s+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def tokenize_words(text: str) -> list[str]:
    return re.findall(r"[A-Za-z']+", text.lower())


def count_syllables(word: str) -> int:
    word = word.lower()
    if not word:
        return 0
    vowels = "aeiouy"
    syllables = 0
    prev_vowel = False
    for ch in word:
        is_vowel = ch in vowels
        if is_vowel and not prev_vowel:
            syllables += 1
        prev_vowel = is_vowel
    if word.endswith("e") and syllables > 1:
        syllables -= 1
    return max(1, syllables)


def rhyme_key(word: str) -> str:
    w = re.sub(r"[^a-z]", "", word.lower())
    if not w:
        return ""
    m = re.search(r"[aeiouy][^aeiouy]*$", w)
    if m:
        return m.group(0)
    return w[-3:]


def section_label_from_tag(tag: str, counters: Dict[str, int]) -> str:
    key = normalize_text(tag).upper()
    key = key.replace("-", "_")
    base = SECTION_ALIASES.get(key, "VERSE")
    counters[base] += 1
    idx = counters[base]
    return f"{base}_{idx}"


def sectionize(clean_text: str) -> tuple[list[dict[str, str]], list[str]]:
    lines_raw = [ln.rstrip() for ln in clean_text.splitlines()]
    counters = defaultdict(int)
    sections: list[dict[str, str]] = []
    collected: list[str] = []
    current_label = "VERSE_1"
    counters["VERSE"] = 1
    for line in lines_raw:
        stripped = line.strip()
        if not stripped:
            continue
        m = re.match(r"^\[(.+?)\]$", stripped)
        if m:
            if collected:
                sections.append({"label": current_label, "lines": collected})
                collected = []
            current_label = section_label_from_tag(m.group(1), counters)
            continue
        collected.append(stripped)
    if collected:
        sections.append({"label": current_label, "lines": collected})
    sections = [s for s in sections if s["lines"]]
    if not sections:
        fallback_lines = [ln for ln in lines_raw if ln.strip()]
        sections = [{"label": "VERSE_1", "lines": fallback_lines}]
    flat_lines: list[str] = []
    for sec in sections:
        flat_lines.extend(sec["lines"])
    return sections, flat_lines

__all__ = [
    "clean_lyrics_text",
    "count_syllables",
    "normalize_text",
    "rhyme_key",
    "section_label_from_tag",
    "sectionize",
    "slugify_song",
    "tokenize_words",
]
