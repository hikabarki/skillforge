"""Score skill selection — and check that the benchmark is worth scoring.

Headline accuracy is the least interesting number here. The report also carries:

* **abstention** — recall on the "nothing fits" items and the false-invocation rate,
  because over-triggering is what actually breaks a skill library in production;
* **confusion by distractor type** — a model that only ever loses to `lexical` hard
  negatives has a different problem than one that loses to `random` fillers;
* **position bias** — accuracy by the gold option's index in the menu; a strong
  gradient means the model is reading order, not descriptions;
* **trivial baselines** — `always_abstain`, `first`, and a bag-of-words `lexical`
  matcher. If the lexical baseline scores near the model, the benchmark is a string
  matching test and any headline number from it is meaningless. Reporting this
  against yourself is cheaper than having a reviewer find it.
"""

from __future__ import annotations

import json
import os
import re
from collections import defaultdict
from typing import Any, Callable

from .schema import ABSTAIN, read_jsonl
from .text import cosine, term_vector

_SKILL_LINE = re.compile(r"^\s*skill\s*[:=]\s*([A-Za-z0-9_\-/.]+)\s*$", re.IGNORECASE | re.MULTILINE)
_STEP_LINE = re.compile(r"^\s*(?:\d+[.)]|[-*+])\s+(.*\S)\s*$", re.MULTILINE)

Predictor = Callable[[dict[str, Any]], str]


def parse_prediction(text: str) -> tuple[str | None, list[str]]:
    """Extract (skill_name, steps) from a model reply. None when nothing parses."""
    m = _SKILL_LINE.search(text or "")
    name = m.group(1) if m else None
    if name and name.upper() == ABSTAIN:
        name = ABSTAIN
    body = text[m.end():] if m else (text or "")
    return name, [s.strip() for s in _STEP_LINE.findall(body)]


# --------------------------------------------------------------------------- baselines

def oracle_predictor(by_name: dict[str, dict[str, Any]]) -> Predictor:
    def predict(traj: dict[str, Any]) -> str:
        return f"skill: {traj['gold_skill']}"
    return predict


def always_abstain_predictor(by_name: dict[str, dict[str, Any]]) -> Predictor:
    def predict(traj: dict[str, Any]) -> str:
        return f"skill: {ABSTAIN}"
    return predict


def first_predictor(by_name: dict[str, dict[str, Any]]) -> Predictor:
    def predict(traj: dict[str, Any]) -> str:
        return f"skill: {traj['menu'][0]}" if traj["menu"] else f"skill: {ABSTAIN}"
    return predict


def lexical_predictor(by_name: dict[str, dict[str, Any]], threshold: float = 0.12) -> Predictor:
    """Bag-of-words nearest description. The honest floor for this task."""
    def predict(traj: dict[str, Any]) -> str:
        tv = term_vector(traj["task"])
        best, best_sim = ABSTAIN, threshold
        for name in traj["menu"]:
            skill = by_name.get(name)
            if not skill:
                continue
            sim = cosine(tv, term_vector(skill["description"]))
            if sim > best_sim:
                best, best_sim = name, sim
        return f"skill: {best}"
    return predict


BASELINES = {
    "oracle": oracle_predictor,
    "always_abstain": always_abstain_predictor,
    "first": first_predictor,
    "lexical": lexical_predictor,
}


# ------------------------------------------------------------------------------ scoring

def _plan_coverage(pred_steps: list[str], gold_steps: list[str]) -> float:
    if not gold_steps:
        return 1.0
    pred_join = " \n ".join(pred_steps).lower()
    hit = sum(1 for g in gold_steps if g.lower()[:40] in pred_join)
    return hit / len(gold_steps)


def score(
    trajectories: list[dict[str, Any]],
    predictions: dict[str, str],
    by_name: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    total = answerable = abstain_total = 0
    correct = answerable_correct = abstain_correct = 0
    false_invocation = unparsed = off_menu = 0
    confusion: dict[str, int] = defaultdict(int)
    by_position: dict[int, list[int]] = defaultdict(list)
    by_kind: dict[str, list[int]] = defaultdict(list)
    plan_scores: list[float] = []
    missing: list[str] = []

    for traj in trajectories:
        tid = traj["trajectory_id"]
        if tid not in predictions:
            missing.append(tid)
            continue
        total += 1
        gold = traj["gold_skill"]
        pred, pred_steps = parse_prediction(predictions[tid])

        if pred is None:
            unparsed += 1
        elif pred != ABSTAIN and pred not in traj["menu"]:
            off_menu += 1

        hit = int(pred == gold)
        correct += hit
        by_kind[traj.get("kind", "select")].append(hit)

        if gold == ABSTAIN:
            abstain_total += 1
            abstain_correct += hit
            if pred not in (ABSTAIN, None):
                false_invocation += 1
                confusion[traj.get("distractor_kinds", {}).get(pred, "unknown")] += 1
        else:
            answerable += 1
            answerable_correct += hit
            if not hit and pred not in (None, ABSTAIN):
                confusion[traj.get("distractor_kinds", {}).get(pred, "unknown")] += 1
            elif not hit and pred == ABSTAIN:
                confusion["over_abstained"] += 1
            if gold in traj["menu"]:
                by_position[traj["menu"].index(gold)].append(hit)
            if traj.get("gold_plan"):
                plan_scores.append(_plan_coverage(pred_steps, traj["gold_plan"]))

    def pct(num: int, den: int) -> float | None:
        """None, not 0.0, when the denominator is empty.

        A rate over zero items is undefined; reporting it as 0.0 makes an absent
        slice look like a total failure and quietly poisons any average taken
        across splits.
        """
        return round(num / den, 4) if den else None

    return {
        "n_scored": total,
        "n_missing_predictions": len(missing),
        "accuracy": pct(correct, total),
        "answerable": {"n": answerable, "accuracy": pct(answerable_correct, answerable)},
        "abstention": {
            "n": abstain_total,
            "recall": pct(abstain_correct, abstain_total),
            "false_invocation_rate": pct(false_invocation, abstain_total),
        },
        "accuracy_by_kind": {
            k: {"n": len(v), "accuracy": pct(sum(v), len(v))} for k, v in sorted(by_kind.items())
        },
        "confusion_by_distractor_kind": dict(sorted(confusion.items())),
        "position_bias": {
            str(pos): {"n": len(v), "accuracy": pct(sum(v), len(v))}
            for pos, v in sorted(by_position.items())
        },
        "plan_coverage_mean": (
            round(sum(plan_scores) / len(plan_scores), 4) if plan_scores else None
        ),
        "parse_failures": unparsed,
        "off_menu_predictions": off_menu,
    }


def run(
    traj_path: str,
    corpus_path: str,
    report_path: str,
    *,
    predictions: str = "lexical",
) -> dict[str, Any]:
    trajectories = list(read_jsonl(traj_path))
    by_name = {s["name"]: s for s in read_jsonl(corpus_path)}

    if predictions in BASELINES:
        predictor = BASELINES[predictions](by_name)
        preds = {t["trajectory_id"]: predictor(t) for t in trajectories}
        source = f"baseline:{predictions}"
    else:
        preds = {}
        for row in read_jsonl(predictions):
            if "trajectory_id" not in row or "prediction" not in row:
                raise ValueError(
                    f"{predictions}: every row needs 'trajectory_id' and 'prediction'"
                )
            preds[row["trajectory_id"]] = row["prediction"]
        source = predictions

    report = score(trajectories, preds, by_name)
    report["predictions"] = source
    report["trajectories"] = traj_path

    if predictions == "oracle" and report["accuracy"] != 1.0:
        raise AssertionError(
            f"oracle scored {report['accuracy']} — the scorer disagrees with the labels, "
            "which means every other number in this report is untrustworthy"
        )

    os.makedirs(os.path.dirname(os.path.abspath(report_path)), exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=2)
    report["report_path"] = report_path
    return report
