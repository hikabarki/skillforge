---
name: incident-postmortem
description: Use this skill when writing a blameless postmortem after an outage — assembling the timeline, separating trigger from root cause, and turning findings into tracked action items. Triggers include 'postmortem', 'incident review', 'write up the outage'.
license: CC-BY-4.0
allowed-tools: [Read, Write]
---

# Blameless postmortem

## Instructions

1. Build the timeline from logs and alerts before asking anyone what happened
2. Separate the trigger from the underlying condition that made it possible
3. Record what made detection slow, separately from what made the fix slow
4. Convert each finding into an owned, dated action item

## Success criteria

- Every timeline entry has a source, not a recollection
- No action item is unowned or undated
- The write-up names systems, never individuals
