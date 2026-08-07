"""skillforge — command line entry point.

    skillforge harvest    fixtures/skills -> data/corpus/skills.jsonl
    skillforge synthesize corpus          -> train/dev trajectories
    skillforge render     trajectories    -> chatml/alpaca SFT rows
    skillforge evaluate   trajectories    -> a report
    skillforge baselines  trajectories    -> the trivial-baseline table
"""

from __future__ import annotations

import argparse
import json
import sys

from . import __version__, evaluate, harvest, render, synthesize
from .schema import read_jsonl


def _emit(obj: dict) -> None:
    printable = {k: v for k, v in obj.items() if k != "rejects"}
    print(json.dumps(printable, ensure_ascii=False, indent=2))


def cmd_harvest(a: argparse.Namespace) -> int:
    stats = harvest.run(a.input, a.out, source=a.source)
    _emit(stats)
    if stats["rejects"]:
        print(f"\n{len(stats['rejects'])} rejected (see {stats['stats_path']}):", file=sys.stderr)
        for r in stats["rejects"][:10]:
            print(f"  {r['path']}: {r['reason']}", file=sys.stderr)
    return 0


def cmd_synthesize(a: argparse.Namespace) -> int:
    _emit(synthesize.run(
        a.corpus, a.out, n_distractors=a.distractors, abstain_rate=a.abstain_rate,
        max_tasks_per_skill=a.max_tasks, dev_fraction=a.dev_fraction, seed=a.seed,
    ))
    return 0


def cmd_render(a: argparse.Namespace) -> int:
    _emit(render.run(a.trajectories, a.out, a.corpus, fmt=a.format))
    return 0


def cmd_evaluate(a: argparse.Namespace) -> int:
    _emit(evaluate.run(a.trajectories, a.corpus, a.report, predictions=a.predictions))
    return 0


def cmd_baselines(a: argparse.Namespace) -> int:
    rows = []
    for name in ("oracle", "always_abstain", "first", "lexical"):
        rep = evaluate.run(
            a.trajectories, a.corpus, f"{a.report_dir}/{name}.json", predictions=name
        )
        rows.append((name, rep["accuracy"], rep["answerable"]["accuracy"],
                     rep["abstention"]["recall"], rep["abstention"]["false_invocation_rate"]))

    width = max(len(r[0]) for r in rows)
    fmt = lambda v, w: ("--".rjust(w) if v is None else f"{v:>{w}.3f}")  # noqa: E731
    print(f"{'baseline'.ljust(width)}  overall  answerable  abstain-recall  false-invoke")
    for name, acc, ans, rec, fir in rows:
        print(f"{name.ljust(width)}  {fmt(acc, 7)}  {fmt(ans, 10)}  "
              f"{fmt(rec, 14)}  {fmt(fir, 12)}")
    return 0


def cmd_stats(a: argparse.Namespace) -> int:
    rows = list(read_jsonl(a.path))
    print(json.dumps({"path": a.path, "rows": len(rows),
                      "keys": sorted(rows[0]) if rows else []}, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="skillforge", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--version", action="version", version=f"skillforge {__version__}")
    sub = p.add_subparsers(dest="command", required=True)

    h = sub.add_parser("harvest", help="normalize a directory of SKILL.md files")
    h.add_argument("--input", required=True)
    h.add_argument("--out", default="data/corpus/skills.jsonl")
    h.add_argument("--source", default=None, help="label for provenance (defaults to dir name)")
    h.set_defaults(func=cmd_harvest)

    s = sub.add_parser("synthesize", help="build trajectories from a corpus")
    s.add_argument("--corpus", default="data/corpus/skills.jsonl")
    s.add_argument("--out", default="data/trajectories/train.jsonl")
    s.add_argument("--distractors", type=int, default=6)
    s.add_argument("--abstain-rate", type=float, default=0.25, dest="abstain_rate")
    s.add_argument("--max-tasks", type=int, default=4, dest="max_tasks")
    s.add_argument("--dev-fraction", type=float, default=0.2, dest="dev_fraction")
    s.add_argument("--seed", type=int, default=20260807)
    s.set_defaults(func=cmd_synthesize)

    r = sub.add_parser("render", help="serialize trajectories as SFT rows")
    r.add_argument("--trajectories", default="data/trajectories/train.jsonl")
    r.add_argument("--corpus", default="data/corpus/skills.jsonl")
    r.add_argument("--out", default="data/trajectories/train.sft.jsonl")
    r.add_argument("--format", choices=["chatml", "alpaca"], default="chatml")
    r.set_defaults(func=cmd_render)

    e = sub.add_parser("evaluate", help="score predictions or a baseline")
    e.add_argument("--trajectories", default="data/trajectories/dev.jsonl")
    e.add_argument("--corpus", default="data/corpus/skills.jsonl")
    e.add_argument("--predictions", default="lexical",
                   help="oracle | always_abstain | first | lexical | path to predictions.jsonl")
    e.add_argument("--report", default="data/reports/report.json")
    e.set_defaults(func=cmd_evaluate)

    b = sub.add_parser("baselines", help="run every trivial baseline and print the table")
    b.add_argument("--trajectories", default="data/trajectories/dev.jsonl")
    b.add_argument("--corpus", default="data/corpus/skills.jsonl")
    b.add_argument("--report-dir", default="data/reports", dest="report_dir")
    b.set_defaults(func=cmd_baselines)

    st = sub.add_parser("stats", help="peek at any JSONL the pipeline produced")
    st.add_argument("path")
    st.set_defaults(func=cmd_stats)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except (ValueError, FileNotFoundError, AssertionError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
