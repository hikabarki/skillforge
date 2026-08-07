#!/usr/bin/env bash
# Validate a SkillForge training config, then hand off to the SFT script.
#
# Every check below runs without a GPU, so a broken config fails in a second on a
# laptop instead of thirty minutes into a rented node.
set -euo pipefail

CONFIG="${1:-}"
if [[ -z "$CONFIG" ]]; then
  echo "usage: $0 <config.yaml> [--dry-run]" >&2
  exit 2
fi

# Resolve before any cd, so a relative path stays valid for the rest of the script.
CONFIG="$(cd "$(dirname "$CONFIG")" && pwd)/$(basename "$CONFIG")"
[[ -f "$CONFIG" ]] || { echo "ERROR: no such config: $CONFIG" >&2; exit 2; }

fail() { echo "ERROR: $*" >&2; exit 1; }

# Placeholders anywhere on the line, not just at end-of-line — a trailing comment
# must not be able to smuggle an unfilled value past this check.
if grep -nE 'PLACEHOLDER|/path/to/(local|your)/' "$CONFIG"; then
  fail "$CONFIG still contains unfilled placeholders (listed above)."
fi

# Required keys must be present AND non-null.
for key in model_id data training lora; do
  grep -qE "^${key}:" "$CONFIG" || fail "$CONFIG has no top-level '${key}:' key."
done
if grep -nE '^[a-z_]+:[[:space:]]*(null|~)[[:space:]]*(#.*)?$' "$CONFIG"; then
  fail "the keys listed above are null; fill them or delete them."
fi

TRAIN_FILE="$(grep -E '^\s+train:' "$CONFIG" | head -1 | sed -E 's/.*train:\s*([^ #]+).*/\1/')"
[[ -f "$TRAIN_FILE" ]] || fail "training data '$TRAIN_FILE' not found — run 'make all' first."

echo "config OK: $CONFIG"
echo "train file: $TRAIN_FILE ($(wc -l < "$TRAIN_FILE") rows)"

if [[ "${2:-}" == "--dry-run" ]]; then
  echo "dry run: stopping before any GPU work."
  exit 0
fi

if ! command -v nvidia-smi >/dev/null 2>&1; then
  fail "no nvidia-smi on PATH. This config has never been run; do not treat it as
       validated for training. Re-run with --dry-run to check the config only."
fi

exec python3 scripts/train/sft_qlora.py --config "$CONFIG"
