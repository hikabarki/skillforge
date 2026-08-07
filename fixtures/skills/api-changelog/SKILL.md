---
name: api-changelog
description: Use this skill when an API surface has changed and consumers need to be told — classifying each change as breaking or additive, writing migration notes, and setting a deprecation window. Triggers include 'changelog', 'breaking change', 'deprecate this endpoint'.
license: Apache-2.0
allowed-tools: [Read, Write]
---

# API changelog

## Instructions

1. Diff the current API surface against the last released one mechanically
2. Classify every difference as additive, behavioral, or breaking
3. Write a migration note for each breaking change with before and after
4. Attach a deprecation window and a removal date to each deprecation

## Success criteria

- Every breaking change has a before/after migration snippet
- Behavioral changes are listed separately from additive ones
- No deprecation is announced without a removal date
