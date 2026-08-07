"""Mine grounded supervision out of a skill — never invent it.

A trajectory needs *tasks* (what a user would plausibly say) and *steps* (what the
skill says to do). Both are taken from the skill's own text. A skill that does not
state them yields fewer trajectories; it does not yield made-up ones. That is the
difference between a dataset you can publish and one you have to caveat.
"""

from __future__ import annotations

import re

_QUOTED = re.compile(r"['\"‘’“”`]([^'\"‘’“”`]{3,60})['\"‘’“”`]")
_USE_WHEN = re.compile(
    r"(?:use (?:this )?(?:skill )?(?:when|whenever|for)|trigger(?:s)? (?:on|include|when)|"
    r"invoke when|applies when)\b(.{10,400}?)(?:(?=\bdo not\b)|(?=\bdon't\b)|(?=\bnever\b)|$)",
    re.IGNORECASE | re.DOTALL,
)
_STEP_HEADING = re.compile(
    r"^#{1,6}\s*(instructions?|steps?|workflow|procedure|how to (?:use|run)|process)\s*$",
    re.IGNORECASE,
)
_STEP_BULLET = re.compile(r"^\s*(?:\d+[.)]|[-*+])\s+(.*\S)\s*$")
_SPLIT = re.compile(r"\s*(?:;|,|\.|—| or | and )\s*")

#: Fragments that describe the *skill's own metadata* rather than a user request.
#: They survive the split cleanly and would otherwise become nonsense tasks.
_META = re.compile(
    r"^(?:trigger|this skill|the skill|use this|examples?\b|includ(?:e|es|ing)\b|requests? to\b)",
    re.IGNORECASE,
)

TASK_TEMPLATES = (
    "{phrase}",
    "I need to {phrase}",
    "Can you help me {phrase}?",
    "{phrase} - how do I get that done?",
    "Please handle this: {phrase}",
)


def _clean(fragment: str) -> str:
    frag = re.sub(r"\s+", " ", fragment).strip(" -–—:;,.")
    frag = re.sub(r"^(?:or|and|also|plus|as well as)\s+", "", frag, flags=re.I)
    frag = re.sub(
        r"^(?:the user (?:wants|asks|needs) to|you (?:are )?(?:should )?)\s*", "", frag, flags=re.I
    )
    return frag.strip()


def trigger_phrases(description: str, body: str = "", *, limit: int = 12) -> list[str]:
    """Phrases the skill itself claims should fire it, longest-first, deduplicated."""
    phrases: list[str] = []

    for m in _USE_WHEN.finditer(description + "\n" + body[:4000]):
        for part in _SPLIT.split(m.group(1)):
            cleaned = _clean(part)
            if 12 <= len(cleaned) <= 140 and " " in cleaned and not _META.match(cleaned):
                phrases.append(cleaned)

    for m in _QUOTED.finditer(description):
        cleaned = _clean(m.group(1))
        if 4 <= len(cleaned) <= 60 and not _META.match(cleaned):
            phrases.append(cleaned)

    seen: set[str] = set()
    out: list[str] = []
    for p in sorted(phrases, key=len, reverse=True):
        key = p.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(p)
    return out[:limit]


def steps(body: str, *, limit: int = 12) -> list[str]:
    """Ordered imperative steps stated under an instructions-style heading."""
    out: list[str] = []
    capturing = False
    for line in body.split("\n"):
        if line.startswith("#"):
            capturing = bool(_STEP_HEADING.match(line.strip()))
            continue
        if not capturing:
            continue
        m = _STEP_BULLET.match(line)
        if m:
            step = _clean(m.group(1))
            if step:
                out.append(step)
        elif line.strip() and not line.startswith(" ") and out:
            capturing = False
    return out[:limit]
