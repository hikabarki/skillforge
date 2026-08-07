# The benchmark

## Item kinds

| Kind | Input | Target |
|:--|:--|:--|
| `select` | request + menu of `name: description` | `skill: <name>` or `skill: NONE` |
| `invoke` | same | the name, then the skill's ordered steps |
| `verify` | same | the name, then the skill's success criteria |

Roughly a quarter of `select` items (configurable via `--abstain-rate`) are
abstention items whose menu contains nothing that fits.

## Distractor types

| Type | How it is chosen | What a loss to it means |
|:--|:--|:--|
| `lexical` | Highest description-cosine to the gold skill | The model cannot separate near-duplicate skills — the interesting failure |
| `same_source` | Same repo, unrelated topic | It is anchoring on house style rather than content |
| `random` | Uniform from the corpus | Something is badly wrong |
| `unrelated` | Filler on abstention menus | Only appears where the answer is `NONE` |

## Reporting a model

```bash
skillforge evaluate --trajectories data/trajectories/dev.jsonl \
                    --predictions preds.jsonl --report data/reports/model.json
skillforge baselines --trajectories data/trajectories/dev.jsonl
```

Publish both. A model number without the `lexical` baseline from the *same* split is
uninterpretable — it is the floor that says how much of the split a string matcher
already solves.

## Validity checks built into the scorer

- `oracle` must score exactly `1.000` or `evaluate` raises. A scorer that disagrees
  with its own labels invalidates every other number in the report.
- `first` measures whether menu order alone carries signal.
- `always_abstain` bounds what refusing everything gets you.
- `position_bias` reports accuracy by the gold option's index. A monotonic gradient
  means the model is reading order, not descriptions.
- Undefined rates are `null`, never `0.0`.
