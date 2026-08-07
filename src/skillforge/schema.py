"""Normalized records that flow through the pipeline.

Every record is a plain dict on disk (JSONL) so the corpus stays inspectable with
`jq` and diffable in git. The dataclasses here are the contract, not the storage.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from typing import Any, Iterable, Iterator

SCHEMA_VERSION = "skillforge/v1"

SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

#: Anthropic's published guidance caps skill descriptions; longer ones are a smell,
#: not an error, so they are flagged rather than rejected.
DESCRIPTION_SOFT_MAX = 1024

ABSTAIN = "NONE"


@dataclass
class Skill:
    """One harvested SKILL.md, normalized."""

    skill_id: str                    # "<source_slug>/<name>", globally unique in a corpus
    name: str                        # slug from frontmatter
    description: str                 # the trigger surface the model actually sees
    body: str                        # markdown after the frontmatter
    source: str                      # repo or directory the skill came from
    path: str                        # path relative to the harvest root
    license: str | None = None
    allowed_tools: list[str] = field(default_factory=list)
    success_criteria: list[str] = field(default_factory=list)
    body_sha256: str = ""
    body_chars: int = 0
    warnings: list[str] = field(default_factory=list)

    def finalize(self) -> "Skill":
        self.body_sha256 = hashlib.sha256(self.body.encode("utf-8")).hexdigest()
        self.body_chars = len(self.body)
        return self

    def card(self) -> str:
        """The compact form shown to the model when it is choosing a skill.

        Deliberately description-only: progressive disclosure means selection has to
        work off the description alone, and an eval that leaks the body measures
        nothing about the real failure mode.
        """
        return f"- {self.name}: {self.description}"

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["schema_version"] = SCHEMA_VERSION
        return d


@dataclass
class Trajectory:
    """One supervised example: a request, a skill menu, and the expected behavior."""

    trajectory_id: str
    task: str                        # the user request
    menu: list[str]                  # skill names offered, in presentation order
    gold_skill: str                  # a skill name, or ABSTAIN
    kind: str                        # "select" | "invoke" | "verify"
    gold_plan: list[str] = field(default_factory=list)
    gold_checks: list[str] = field(default_factory=list)
    distractor_kinds: dict[str, str] = field(default_factory=dict)
    provenance: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["schema_version"] = SCHEMA_VERSION
        return d


def is_slug(value: str) -> bool:
    return bool(SLUG_RE.match(value))


def write_jsonl(path: str, records: Iterable[Any]) -> int:
    n = 0
    with open(path, "w", encoding="utf-8") as fh:
        for rec in records:
            payload = rec.to_dict() if hasattr(rec, "to_dict") else rec
            fh.write(json.dumps(payload, ensure_ascii=False) + "\n")
            n += 1
    return n


def read_jsonl(path: str) -> Iterator[dict[str, Any]]:
    with open(path, encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{lineno}: malformed JSON — {exc}") from exc
