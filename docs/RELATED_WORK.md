# Related work

Where SkillForge sits relative to the 2026 agent-skill literature. Read these before
claiming novelty for anything here.

| Work | What it does | What SkillForge does differently |
|:--|:--|:--|
| [SkillsBench (2602.12670)](https://arxiv.org/abs/2602.12670) | Benchmarks how much agent skills help across diverse tasks | Targets *selection under distractors and abstention* rather than end-task lift |
| [OpenSkillEval (2605.23657)](https://arxiv.org/abs/2605.23657) | Automatically audits the open skill ecosystem for quality and risk | Consumes skills as training data rather than auditing them; the harvester's warnings are a thin overlap |
| [Agent Skill Evaluation and Evolution (2606.11435)](https://arxiv.org/abs/2606.11435) | Frameworks and benchmarks for skill evaluation and evolution | Fixed skill set; the variable is the model, not the skill library |
| [SkillCorpus (2607.15557)](https://arxiv.org/abs/2607.15557) | Consolidates and evaluates the open skill ecosystem | A natural upstream — a consolidated corpus is exactly what `harvest` wants pointed at it |
| [Skill Retrieval Augmentation (2604.24594)](https://arxiv.org/html/2604.24594v1) | Retrieval over a large skill library | Complementary: retrieval narrows the menu, SkillForge measures choosing within it |
| [ContinualSkillBench (2608.03874)](https://arxiv.org/html/2608.03874) | Whether agents genuinely evolve capabilities over time | Single-shot selection, no continual-learning axis |

## The claim

Not "a new benchmark for skills" — several exist. The specific gap is that skill use
is evaluated zero-shot on frontier models and never treated as a **fine-tuning
target** for small open models, and that selection benchmarks generally omit
abstention items, which hides the over-triggering failure mode entirely.

If a paper already does exactly this, the honest move is to cite it and pivot to the
Korean/multilingual axis — no published skill corpus is non-English, and
`docs/DESIGN.md` lists that as an open item rather than a solved one.
