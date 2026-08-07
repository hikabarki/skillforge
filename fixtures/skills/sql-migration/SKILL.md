---
name: sql-migration
description: Use this skill when the user needs a database schema change written as a reversible migration — adding columns, backfilling data, changing constraints, or splitting a table. Triggers include 'migration', 'alter table', 'backfill', 'schema change'. Do not use for one-off analytical queries.
license: Apache-2.0
allowed-tools: [Read, Write, Bash]
---

# Reversible schema migration

## Instructions

1. Write the down migration before the up migration
2. Split any change that locks a large table into additive and destructive halves
3. Backfill in bounded batches with an explicit resume key
4. Ship the additive half, verify, then ship the destructive half separately
5. Rehearse the rollback on a restored snapshot

## Success criteria

- The down migration restores the schema exactly
- No single statement holds an exclusive lock on a hot table
- The backfill is resumable after being killed mid-run
