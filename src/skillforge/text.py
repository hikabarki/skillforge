"""Tokenization and overlap. Shared by the distractor sampler and the lexical baseline
so that "hard negative" and "what a string matcher can already solve" use the same
notion of similarity — otherwise the difficulty knob and the validity check disagree.
"""

from __future__ import annotations

import math
import re
from collections import Counter

_TOKEN = re.compile(r"[a-z0-9]+(?:[.\-_][a-z0-9]+)*")

STOPWORDS = frozenset(
    """a an the this that these those and or but if then else when while for to of in on at by
    with from into over under about as is are was were be been being do does did doing use uses
    used using user users it its their there here they them you your i we our not no any all can
    should would could may might will shall want wants need needs get gets make makes""".split()
)


def tokenize(text: str) -> list[str]:
    return [t for t in _TOKEN.findall(text.lower()) if t not in STOPWORDS and len(t) > 1]


def term_vector(text: str) -> "Counter[str]":
    return Counter(tokenize(text))


def cosine(a: "Counter[str]", b: "Counter[str]") -> float:
    if not a or not b:
        return 0.0
    common = set(a) & set(b)
    num = sum(a[t] * b[t] for t in common)
    if num == 0:
        return 0.0
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    return num / (na * nb)


def jaccard(a: str, b: str) -> float:
    sa, sb = set(tokenize(a)), set(tokenize(b))
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)
