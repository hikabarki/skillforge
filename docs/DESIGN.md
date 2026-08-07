# Design

## Why grounded mining instead of an LLM generator

The obvious way to build this dataset is to prompt a strong model: "here is a skill,
write ten user requests that should trigger it." It is faster and produces more
natural language. It also makes the corpus unreproducible, licence-entangled, and
quietly biased toward whatever the generator thinks skills are for — and it means the
benchmark measures agreement with the generator rather than agreement with the skill.

SkillForge instead mines supervision from the skill's own text:

| Signal | Mined from |
|:--|:--|
| Task | `Use this skill when ...`, `Triggers include ...`, and quoted phrases in `description` |
| Plan | Ordered bullets under an `## Instructions` / `## Steps` / `## Workflow` heading |
| Checks | Bullets under a `## Success criteria` / `## Definition of done` heading |

A skill that states none of these produces no rows, and the count lands in
`synth_stats.json` under `skipped`. That is the honest outcome: the alternative is
inventing a trigger surface, and an invented trigger surface is precisely the noise
this benchmark exists to detect.

An optional LLM paraphrase stage is a reasonable future addition — as an
*augmentation* on top of the grounded core, flagged per-row via
`provenance.grounded`, never as the source of truth.

## Why selection sees descriptions only

Progressive disclosure is the whole point of the skill format: the runtime shows the
model a list of names and descriptions, and reveals the body only after one is
chosen. An eval that pastes bodies into the menu is measuring long-context reading
comprehension. `render.build_prompt` therefore emits `name: description` and nothing
else, and a test asserts the gold skill is reachable from the rendered prompt.

## Why abstention items are constructed, not sampled

An abstention item is built by taking a real request and assembling a menu from
skills that are *far* from the origin skill (description cosine ≤ `0.10`) and far
from the request text (token Jaccard ≤ `0.12`). Both thresholds matter: filtering
only on the origin skill lets a filler sneak in that happens to match the request
wording, which turns a labelled-unanswerable item into an ambiguous one. When the
corpus cannot supply a clean menu, the item is skipped and counted under
`skipped.no_abstain_menu` rather than emitted with a shaky label.

## Why the holdout is by skill

Two skills from the same repo share vocabulary, structure and phrasing. A row-level
split puts near-identical rows on both sides and reports a number that mostly
measures memorization. `split_by_skill` holds out whole `skill_id`s, so dev asks the
question that matters: does this generalize to a skill the model has never seen?

## Why the prompt lives in one module

`render.build_prompt` is imported by both the SFT renderer and the evaluator. A
benchmark score produced against a prompt the model was not trained under is a very
easy mistake to make and a very hard one to notice — the numbers simply come out
lower and everyone blames the model.

## Failure modes this design does not cover

- **Multi-skill tasks.** Every item has exactly one gold skill or none. Requests that
  legitimately need two skills composed are out of scope for v1.
- **Adversarial skills.** A skill whose description is written to capture unrelated
  traffic is a real ecosystem problem and is not modelled here.
- **Execution.** `invoke` items score whether the model reproduces the prescribed
  plan, not whether running that plan works.
