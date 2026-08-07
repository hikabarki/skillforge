"""Turn a harvested corpus into supervised trajectories.

Three item kinds, all grounded in the skill's own text:

    select  — a request + a menu of skill descriptions; pick one name, or abstain
    invoke  — the same, plus the ordered steps the chosen skill states
    verify  — check a claimed result against the skill's stated success criteria

Two things make this a benchmark rather than a pile of examples:

1. **Typed distractors.** Every wrong option on the menu is labelled `lexical`
   (nearest neighbour by description similarity), `same_source`, or `random`. Which
   type steals the pick is the diagnostic — an accuracy number alone hides it.

2. **Abstention items.** A quarter of the menu (by default) contains no skill that
   fits. Over-triggering is the dominant real-world failure of skill ecosystems and
   a benchmark without abstention items cannot see it at all.

Holdout is by *skill*, not by row: the question worth answering is whether a model
generalizes to skills it has never seen, and a row-level split answers a much easier
question while looking identical on a scoreboard.
"""

from __future__ import annotations

import hashlib
import json
import os
import random
from typing import Any

from .mine import TASK_TEMPLATES, steps, trigger_phrases
from .schema import ABSTAIN, Trajectory, read_jsonl, write_jsonl
from .text import cosine, jaccard, term_vector

#: Above this description-similarity a skill is too close to be a safe "no skill fits"
#: filler. Tuned so abstention items are genuinely unanswerable, not merely hard.
ABSTAIN_SIM_MAX = 0.10
#: And the filler must not overlap the request text itself.
ABSTAIN_TASK_JACCARD_MAX = 0.12


def _rid(*parts: str) -> str:
    return hashlib.sha256("␟".join(parts).encode("utf-8")).hexdigest()[:16]


def _rank_neighbors(skills: list[dict[str, Any]]) -> dict[str, list[tuple[str, float]]]:
    vecs = {s["name"]: term_vector(s["description"]) for s in skills}
    ranked: dict[str, list[tuple[str, float]]] = {}
    for s in skills:
        me = s["name"]
        scored = [(o["name"], cosine(vecs[me], vecs[o["name"]])) for o in skills if o["name"] != me]
        scored.sort(key=lambda kv: (-kv[1], kv[0]))
        ranked[me] = scored
    return ranked


def _build_menu(
    gold: str,
    neighbors: list[tuple[str, float]],
    pool: list[str],
    n_distractors: int,
    rng: random.Random,
    source_of: dict[str, str],
) -> tuple[list[str], dict[str, str]]:
    """Half lexical hard negatives, the rest same-source then random."""
    kinds: dict[str, str] = {}
    chosen: list[str] = []

    n_lex = max(1, n_distractors // 2)
    for name, sim in neighbors:
        if len(chosen) >= n_lex:
            break
        if sim <= 0.0:
            break
        chosen.append(name)
        kinds[name] = "lexical"

    same_source = [
        n for n in pool if n != gold and n not in kinds and source_of.get(n) == source_of.get(gold)
    ]
    rng.shuffle(same_source)
    for name in same_source:
        if len(chosen) >= n_distractors:
            break
        chosen.append(name)
        kinds[name] = "same_source"

    rest = [n for n in pool if n != gold and n not in kinds]
    rng.shuffle(rest)
    for name in rest:
        if len(chosen) >= n_distractors:
            break
        chosen.append(name)
        kinds[name] = "random"

    menu = chosen + [gold]
    rng.shuffle(menu)
    return menu, kinds


def _abstain_menu(
    origin: str,
    task: str,
    neighbors: list[tuple[str, float]],
    by_name: dict[str, dict[str, Any]],
    n_options: int,
    rng: random.Random,
) -> tuple[list[str], dict[str, str]] | None:
    """A menu on which nothing fits. Returns None when the corpus cannot supply one."""
    too_close = {name for name, sim in neighbors if sim > ABSTAIN_SIM_MAX}
    candidates = [
        name
        for name in by_name
        if name != origin
        and name not in too_close
        and jaccard(task, by_name[name]["description"]) <= ABSTAIN_TASK_JACCARD_MAX
    ]
    if len(candidates) < 2:
        return None
    rng.shuffle(candidates)
    menu = candidates[:n_options]
    return menu, {name: "unrelated" for name in menu}


def synthesize(
    skills: list[dict[str, Any]],
    *,
    n_distractors: int = 6,
    abstain_rate: float = 0.25,
    max_tasks_per_skill: int = 4,
    seed: int = 20260807,
) -> tuple[list[Trajectory], dict[str, Any]]:
    rng = random.Random(seed)
    by_name = {s["name"]: s for s in skills}
    source_of = {s["name"]: s.get("source", "") for s in skills}
    pool = sorted(by_name)
    neighbors = _rank_neighbors(skills)

    trajectories: list[Trajectory] = []
    skipped: dict[str, int] = {"no_trigger_phrase": 0, "no_steps": 0, "no_criteria": 0,
                               "no_abstain_menu": 0}

    for skill in sorted(skills, key=lambda s: s["name"]):
        name = skill["name"]
        phrases = trigger_phrases(skill["description"], skill.get("body", ""))
        if not phrases:
            skipped["no_trigger_phrase"] += 1
            continue

        plan = steps(skill.get("body", ""))
        checks = skill.get("success_criteria") or []
        if not plan:
            skipped["no_steps"] += 1
        if not checks:
            skipped["no_criteria"] += 1

        for i, phrase in enumerate(phrases[:max_tasks_per_skill]):
            task = TASK_TEMPLATES[i % len(TASK_TEMPLATES)].format(phrase=phrase)
            prov = {
                "skill_id": skill.get("skill_id", name),
                "source": skill.get("source", ""),
                "license": skill.get("license"),
                "trigger_phrase": phrase,
                "template_index": i % len(TASK_TEMPLATES),
                "grounded": True,
            }

            menu, kinds = _build_menu(name, neighbors[name], pool, n_distractors, rng, source_of)
            trajectories.append(
                Trajectory(
                    trajectory_id=_rid("select", name, task),
                    task=task, menu=menu, gold_skill=name, kind="select",
                    distractor_kinds=kinds, provenance=prov,
                )
            )

            if plan:
                menu_i, kinds_i = _build_menu(
                    name, neighbors[name], pool, n_distractors, rng, source_of
                )
                trajectories.append(
                    Trajectory(
                        trajectory_id=_rid("invoke", name, task),
                        task=task, menu=menu_i, gold_skill=name, kind="invoke",
                        gold_plan=plan, distractor_kinds=kinds_i, provenance=prov,
                    )
                )

            if checks:
                menu_v, kinds_v = _build_menu(
                    name, neighbors[name], pool, n_distractors, rng, source_of
                )
                trajectories.append(
                    Trajectory(
                        trajectory_id=_rid("verify", name, task),
                        task=task, menu=menu_v, gold_skill=name, kind="verify",
                        gold_checks=checks, distractor_kinds=kinds_v, provenance=prov,
                    )
                )

            if rng.random() < abstain_rate:
                built = _abstain_menu(
                    name, task, neighbors[name], by_name, n_distractors + 1, rng
                )
                if built is None:
                    skipped["no_abstain_menu"] += 1
                else:
                    menu_a, kinds_a = built
                    trajectories.append(
                        Trajectory(
                            trajectory_id=_rid("abstain", name, task),
                            task=task, menu=menu_a, gold_skill=ABSTAIN, kind="select",
                            distractor_kinds=kinds_a,
                            provenance={**prov, "abstain_origin": name},
                        )
                    )

    stats = {
        "skills_in": len(skills),
        "skills_used": len({t.provenance.get("skill_id") for t in trajectories}),
        "trajectories": len(trajectories),
        "by_kind": {
            k: sum(1 for t in trajectories if t.kind == k) for k in ("select", "invoke", "verify")
        },
        "abstain_items": sum(1 for t in trajectories if t.gold_skill == ABSTAIN),
        "distractor_kind_counts": _kind_histogram(trajectories),
        "skipped": skipped,
        "params": {
            "n_distractors": n_distractors, "abstain_rate": abstain_rate,
            "max_tasks_per_skill": max_tasks_per_skill, "seed": seed,
            "abstain_sim_max": ABSTAIN_SIM_MAX,
        },
    }
    return trajectories, stats


def _kind_histogram(trajectories: list[Trajectory]) -> dict[str, int]:
    hist: dict[str, int] = {}
    for t in trajectories:
        for kind in t.distractor_kinds.values():
            hist[kind] = hist.get(kind, 0) + 1
    return hist


def split_by_skill(
    trajectories: list[Trajectory], dev_fraction: float, seed: int
) -> tuple[list[Trajectory], list[Trajectory]]:
    """Hold out whole skills, so dev measures generalization to unseen skills."""
    rng = random.Random(seed)
    names = sorted({str(t.provenance.get("skill_id")) for t in trajectories})
    rng.shuffle(names)
    n_dev = max(1, round(len(names) * dev_fraction)) if dev_fraction > 0 else 0
    dev_ids = set(names[:n_dev])
    train = [t for t in trajectories if str(t.provenance.get("skill_id")) not in dev_ids]
    dev = [t for t in trajectories if str(t.provenance.get("skill_id")) in dev_ids]
    return train, dev


def run(
    corpus_path: str,
    out_path: str,
    *,
    n_distractors: int = 6,
    abstain_rate: float = 0.25,
    max_tasks_per_skill: int = 4,
    dev_fraction: float = 0.2,
    seed: int = 20260807,
) -> dict[str, Any]:
    skills = list(read_jsonl(corpus_path))
    if not skills:
        raise ValueError(f"{corpus_path} is empty — run `harvest` first")

    trajectories, stats = synthesize(
        skills, n_distractors=n_distractors, abstain_rate=abstain_rate,
        max_tasks_per_skill=max_tasks_per_skill, seed=seed,
    )
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)

    train, dev = split_by_skill(trajectories, dev_fraction, seed)
    write_jsonl(out_path, train)
    dev_path = os.path.splitext(out_path)[0].replace("train", "dev") + ".jsonl"
    if dev_path == out_path:
        dev_path = os.path.splitext(out_path)[0] + ".dev.jsonl"
    write_jsonl(dev_path, dev)

    stats["train_rows"] = len(train)
    stats["dev_rows"] = len(dev)
    stats["dev_path"] = dev_path
    stats["holdout"] = "by skill (no skill appears in both splits)"
    stats_path = os.path.splitext(out_path)[0] + ".synth_stats.json"
    with open(stats_path, "w", encoding="utf-8") as fh:
        json.dump(stats, fh, ensure_ascii=False, indent=2)
    stats["stats_path"] = stats_path
    return stats
