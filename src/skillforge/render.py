"""Prompt construction and SFT serialization.

This module is the single source of truth for the prompt. Training and evaluation
both import `build_prompt`, so a benchmark score can never be produced against a
prompt the model was not actually trained under — a mismatch that is easy to create
by accident and nearly invisible once it exists.

Selection sees descriptions only. That is progressive disclosure as the real runtime
does it: the body is revealed *after* a skill is chosen, so an eval that pastes the
body into the menu is measuring reading comprehension, not skill selection.
"""

from __future__ import annotations

import json
import os
from typing import Any

from .schema import ABSTAIN, read_jsonl

SYSTEM = (
    "You are an agent with a library of skills. Given a request and a menu of skills, "
    "select the single skill that applies, or answer "
    f"{ABSTAIN} when none of them does. Answering {ABSTAIN} is correct and expected "
    "whenever no listed skill genuinely covers the request; never stretch a skill to fit."
)

_INSTRUCTION = {
    "select": (
        "Reply with exactly one line:\n"
        "skill: <name>   (or  skill: " + ABSTAIN + ")"
    ),
    "invoke": (
        "Reply with the chosen skill, then the ordered steps that skill prescribes:\n"
        "skill: <name>\nplan:\n1. <step>\n2. <step>\n"
        "If no skill applies, reply `skill: " + ABSTAIN + "` with no plan."
    ),
    "verify": (
        "Reply with the chosen skill, then the checks that must pass before the work "
        "is considered done:\n"
        "skill: <name>\nchecks:\n- <check>\n- <check>\n"
        "If no skill applies, reply `skill: " + ABSTAIN + "` with no checks."
    ),
}


def build_prompt(traj: dict[str, Any], by_name: dict[str, dict[str, Any]]) -> str:
    lines = ["### Request", traj["task"], "", "### Available skills"]
    for name in traj["menu"]:
        skill = by_name.get(name)
        desc = skill["description"] if skill else "(description unavailable)"
        lines.append(f"- {name}: {desc}")
    lines += ["", _INSTRUCTION.get(traj.get("kind", "select"), _INSTRUCTION["select"])]
    return "\n".join(lines)


def build_target(traj: dict[str, Any]) -> str:
    gold = traj["gold_skill"]
    if gold == ABSTAIN:
        return f"skill: {ABSTAIN}"
    kind = traj.get("kind", "select")
    if kind == "invoke" and traj.get("gold_plan"):
        steps = "\n".join(f"{i}. {s}" for i, s in enumerate(traj["gold_plan"], 1))
        return f"skill: {gold}\nplan:\n{steps}"
    if kind == "verify" and traj.get("gold_checks"):
        checks = "\n".join(f"- {c}" for c in traj["gold_checks"])
        return f"skill: {gold}\nchecks:\n{checks}"
    return f"skill: {gold}"


def to_chatml(traj: dict[str, Any], by_name: dict[str, dict[str, Any]]) -> dict[str, Any]:
    return {
        "id": traj["trajectory_id"],
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": build_prompt(traj, by_name)},
            {"role": "assistant", "content": build_target(traj)},
        ],
        "meta": {
            "kind": traj.get("kind"),
            "gold_skill": traj["gold_skill"],
            "abstain": traj["gold_skill"] == ABSTAIN,
            "n_options": len(traj["menu"]),
            "source": traj.get("provenance", {}).get("source"),
            "license": traj.get("provenance", {}).get("license"),
        },
    }


def to_alpaca(traj: dict[str, Any], by_name: dict[str, dict[str, Any]]) -> dict[str, Any]:
    return {
        "id": traj["trajectory_id"],
        "instruction": SYSTEM,
        "input": build_prompt(traj, by_name),
        "output": build_target(traj),
    }


def run(traj_path: str, out_path: str, corpus_path: str, *, fmt: str = "chatml") -> dict[str, Any]:
    by_name = {s["name"]: s for s in read_jsonl(corpus_path)}
    convert = {"chatml": to_chatml, "alpaca": to_alpaca}[fmt]
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)

    n = 0
    with open(out_path, "w", encoding="utf-8") as fh:
        for traj in read_jsonl(traj_path):
            fh.write(json.dumps(convert(traj, by_name), ensure_ascii=False) + "\n")
            n += 1
    return {"format": fmt, "rows": n, "out": out_path}
