---
name: csv-clean
description: Use this skill when the user has a messy delimited data file — a .csv or .tsv with malformed rows, headers in the wrong place, mixed encodings, or junk padding — and wants it turned into clean tabular data. Triggers include 'clean this csv', 'fix the headers', 'the file has junk rows'. Do not use when the deliverable is a formatted Excel model.
license: MIT
allowed-tools: [Read, Write, Bash]
---

# Delimited data cleaner

## Instructions

1. Detect the encoding and delimiter before parsing a single row
2. Locate the true header row and record how many junk rows precede it
3. Normalize column names to snake_case without renaming semantics
4. Quarantine rows whose field count disagrees with the header
5. Write the cleaned file and a rejects file, never a merged one

## Success criteria

- Every output row has exactly as many fields as the header
- Quarantined rows are written out, not silently dropped
- The original file is left unmodified
