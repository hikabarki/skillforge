---
name: git-bisect
description: Use this skill when a regression appeared somewhere in a range of commits and the user needs to find which commit introduced it. Triggers include 'bisect', 'which commit broke', 'it worked last week'. Do not use when the failing commit is already known.
license: Apache-2.0
allowed-tools: [Bash, Read]
---

# Regression bisect

## Instructions

1. Write a test that fails on the bad commit and passes on the known-good one
2. Make that test exit non-zero deterministically, with no network dependency
3. Run the bisect driven by the script rather than by hand
4. Confirm the culprit by reverting it in isolation

## Success criteria

- The reproduction script is deterministic across three consecutive runs
- The culprit commit is confirmed by revert, not by inference
- The bisect log is saved with the finding
