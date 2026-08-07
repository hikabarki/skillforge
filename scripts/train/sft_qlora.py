"""QLoRA SFT over rendered SkillForge trajectories.

Heavy imports are deferred so `--check` works on a machine with no torch: the point
is to catch config mistakes before renting a GPU, not after.

This script has never been executed — there is no GPU in the development
environment. Treat it as a reviewed starting point, not a validated recipe.
"""

from __future__ import annotations

import argparse
import json
import sys


def load_config(path: str) -> dict:
    try:
        import yaml
    except ImportError:  # pragma: no cover - depends on optional extra
        sys.exit("PyYAML is required to read configs: pip install -e '.[train]'")
    with open(path, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def check(cfg: dict) -> None:
    if str(cfg.get("model_id", "")).startswith("PLACEHOLDER"):
        sys.exit("model_id is still a placeholder — point it at a checkpoint you have pulled.")
    if cfg.get("data", {}).get("packing"):
        sys.exit(
            "packing must stay false: packed sequences splice one example's skill menu "
            "onto another's target, which silently corrupts the selection task."
        )
    if not cfg.get("completion_only_loss", False):
        sys.exit(
            "completion_only_loss must be true, or the loss rewards reproducing the "
            "skill menu rather than choosing from it."
        )
    n = sum(1 for _ in open(cfg["data"]["train"], encoding="utf-8"))
    print(json.dumps({"config_ok": True, "train_rows": n, "model_id": cfg["model_id"]}, indent=2))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--config", required=True)
    ap.add_argument("--check", action="store_true", help="validate config and data, then stop")
    args = ap.parse_args()

    cfg = load_config(args.config)
    check(cfg)
    if args.check:
        return 0

    from datasets import load_dataset          # noqa: PLC0415
    from peft import LoraConfig                # noqa: PLC0415
    from transformers import AutoTokenizer, BitsAndBytesConfig  # noqa: PLC0415
    from trl import SFTConfig, SFTTrainer      # noqa: PLC0415
    import torch                               # noqa: PLC0415

    q = cfg["quantization"]
    bnb = BitsAndBytesConfig(
        load_in_4bit=q["load_in_4bit"],
        bnb_4bit_quant_type=q["bnb_4bit_quant_type"],
        bnb_4bit_compute_dtype=getattr(torch, q["bnb_4bit_compute_dtype"]),
        bnb_4bit_use_double_quant=q["bnb_4bit_use_double_quant"],
    )
    tok = AutoTokenizer.from_pretrained(cfg["model_id"])
    ds = load_dataset(
        "json",
        data_files={"train": cfg["data"]["train"], "eval": cfg["data"]["eval"]},
    )
    trainer = SFTTrainer(
        model=cfg["model_id"],
        args=SFTConfig(
            **cfg["training"],
            max_length=cfg["data"]["max_seq_length"],
            packing=cfg["data"]["packing"],
            completion_only_loss=cfg["completion_only_loss"],
            model_init_kwargs={"quantization_config": bnb, "dtype": torch.bfloat16},
        ),
        train_dataset=ds["train"],
        eval_dataset=ds["eval"],
        peft_config=LoraConfig(**cfg["lora"]),
        processing_class=tok,
    )
    trainer.train()
    trainer.save_model(cfg["training"]["output_dir"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
