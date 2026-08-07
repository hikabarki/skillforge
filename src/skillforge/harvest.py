"""Walk a directory of skills, normalize each SKILL.md, and report what was rejected.

Rejects are written out with a reason. Nothing is repaired by inference: a skill with
a missing description is a skill whose trigger surface we would have to invent, and
invented trigger text is exactly the noise this dataset exists to measure.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any

from .frontmatter import FrontmatterError, parse
from .schema import DESCRIPTION_SOFT_MAX, Skill, is_slug, write_jsonl

SKILL_FILENAMES = ("SKILL.md", "skill.md")

_CRITERIA_HEADINGS = re.compile(
    r"^#{1,6}\s*(success criteria|acceptance criteria|definition of done|checklist|"
    r"verification|validation)\s*$",
    re.IGNORECASE,
)
_BULLET = re.compile(r"^\s*(?:[-*+]|\d+\.)\s+(.*\S)\s*$")


def extract_success_criteria(body: str) -> list[str]:
    """Pull bullets under a success-criteria-ish heading. Empty list when absent."""
    out: list[str] = []
    capturing = False
    for line in body.split("\n"):
        if line.startswith("#"):
            capturing = bool(_CRITERIA_HEADINGS.match(line.strip()))
            continue
        if capturing:
            m = _BULLET.match(line)
            if m:
                out.append(m.group(1))
            elif line.strip() and not line.startswith(" "):
                capturing = False
    return out


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v) for v in value if v is not None]
    return [str(value)]


def normalize(text: str, *, source: str, rel_path: str) -> Skill:
    """Parse one SKILL.md into a Skill. Raises ValueError with a human reason."""
    meta, body = parse(text)

    name = meta.get("name")
    if not name or not isinstance(name, str):
        raise ValueError("frontmatter has no 'name'")
    description = meta.get("description")
    if not description or not isinstance(description, str):
        raise ValueError("frontmatter has no 'description' — the trigger surface is missing")

    warnings: list[str] = []
    if not is_slug(name):
        warnings.append(f"name {name!r} is not a lowercase-hyphen slug")
    if len(description) > DESCRIPTION_SOFT_MAX:
        warnings.append(f"description is {len(description)} chars (> {DESCRIPTION_SOFT_MAX})")
    if not body.strip():
        warnings.append("body is empty — nothing to disclose after selection")
    if "license" not in meta:
        warnings.append("no license in frontmatter — redistribution status unknown")

    source_slug = re.sub(r"[^a-z0-9]+", "-", source.lower()).strip("-") or "local"

    return Skill(
        skill_id=f"{source_slug}/{name}",
        name=name,
        description=description.strip(),
        body=body,
        source=source,
        path=rel_path.replace(os.sep, "/"),
        license=meta.get("license"),
        allowed_tools=_as_list(meta.get("allowed-tools") or meta.get("allowed_tools")),
        success_criteria=extract_success_criteria(body),
        warnings=warnings,
    ).finalize()


def discover(root: str) -> list[str]:
    found: list[str] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in {".git", "node_modules", "__pycache__"}]
        for fname in filenames:
            if fname in SKILL_FILENAMES:
                found.append(os.path.join(dirpath, fname))
    return sorted(found)


def harvest(root: str, *, source: str | None = None) -> tuple[list[Skill], list[dict[str, str]]]:
    source = source or os.path.basename(os.path.abspath(root))
    skills: list[Skill] = []
    rejects: list[dict[str, str]] = []
    seen: dict[str, str] = {}

    for path in discover(root):
        rel = os.path.relpath(path, root)
        try:
            with open(path, encoding="utf-8") as fh:
                text = fh.read()
            skill = normalize(text, source=source, rel_path=rel)
        except (FrontmatterError, ValueError, UnicodeDecodeError) as exc:
            rejects.append({"path": rel.replace(os.sep, "/"), "reason": str(exc)})
            continue

        if skill.skill_id in seen:
            rejects.append(
                {
                    "path": skill.path,
                    "reason": f"duplicate skill_id {skill.skill_id!r} (first seen at "
                    f"{seen[skill.skill_id]}) — names must be unique within a source",
                }
            )
            continue
        seen[skill.skill_id] = skill.path
        skills.append(skill)

    return skills, rejects


def run(root: str, out_path: str, *, source: str | None = None) -> dict[str, Any]:
    skills, rejects = harvest(root, source=source)
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    n = write_jsonl(out_path, skills)

    stats = {
        "root": root,
        "skills_written": n,
        "rejected": len(rejects),
        "rejects": rejects,
        "with_warnings": sum(1 for s in skills if s.warnings),
        "without_license": sum(1 for s in skills if not s.license),
        "with_success_criteria": sum(1 for s in skills if s.success_criteria),
        "median_description_chars": (
            sorted(len(s.description) for s in skills)[len(skills) // 2] if skills else 0
        ),
    }
    stats_path = os.path.splitext(out_path)[0] + ".harvest_stats.json"
    with open(stats_path, "w", encoding="utf-8") as fh:
        json.dump(stats, fh, ensure_ascii=False, indent=2)
    stats["stats_path"] = stats_path
    return stats
