# Licensing a harvested corpus

An Apache-2.0 pipeline does not make a harvested corpus redistributable. Each skill
carries its own terms, and the terms travel with the text.

## What the harvester records

Every row in `skills.jsonl` carries `license`, `source` and `path`. A skill with no
`license:` in its frontmatter is **not** assumed permissive — it gets a warning
(`no license in frontmatter — redistribution status unknown`) and shows up in
`harvest_stats.json` under `without_license`.

## Before publishing a corpus

1. `jq -r '.license' data/corpus/skills.jsonl | sort | uniq -c` — know the mix.
2. Drop everything with an unknown license, or get it in writing.
3. Check for `NC` / `ND` terms. Non-commercial and no-derivatives clauses both bite:
   a derived SFT corpus is a derivative work.
4. Attribute per-skill, not per-corpus, for anything CC-BY family.
5. Publish `harvest_stats.json` alongside the corpus so the audit is reproducible.

## What the derived trajectories inherit

Trajectories quote the skill's description, steps and criteria verbatim. They are
derivative works of the skill, and `provenance.license` on every row is there so the
inheritance is queryable rather than assumed. The rendered SFT file carries it too,
under `meta.license`.

## Trained adapters

An adapter's releasable license is determined by the data it was trained on, not by
this repository's license file.
