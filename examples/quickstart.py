"""Reproduce fixture baselines without a GPU or package installation."""

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
environment = os.environ.copy()
environment["PYTHONPATH"] = str(ROOT / "src")
environment["PYTHONIOENCODING"] = "utf-8"
commands = [
    ["harvest", "--input", "fixtures/skills", "--out", "examples/generated/skills.jsonl"],
    [
        "synthesize",
        "--corpus",
        "examples/generated/skills.jsonl",
        "--out",
        "examples/generated/train.jsonl",
        "--distractors",
        "6",
        "--abstain-rate",
        "0.25",
        "--seed",
        "20260807",
    ],
    [
        "render",
        "--corpus",
        "examples/generated/skills.jsonl",
        "--trajectories",
        "examples/generated/train.jsonl",
        "--out",
        "examples/generated/train.sft.jsonl",
        "--format",
        "chatml",
    ],
    [
        "baselines",
        "--corpus",
        "examples/generated/skills.jsonl",
        "--trajectories",
        "examples/generated/train.jsonl",
        "--report-dir",
        "examples/generated/reports",
    ],
]
for command in commands:
    subprocess.run(
        [sys.executable, "-m", "skillforge.cli", *command], cwd=ROOT, env=environment, check=True
    )
print("Fixture baselines only: no model was trained or evaluated.")
