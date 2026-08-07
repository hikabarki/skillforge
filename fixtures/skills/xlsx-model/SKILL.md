---
name: xlsx-model
description: Use this skill when the user wants to build or repair a spreadsheet model — adding computed columns, writing formulas, formatting, or charting inside an .xlsx or .xlsm workbook. Triggers include 'spreadsheet', 'excel', 'workbook', '.xlsx'. Do not use when the deliverable is a Word document or a standalone script.
license: Apache-2.0
allowed-tools: [Read, Write, Bash]
---

# Spreadsheet model builder

## Instructions

1. Map the existing sheets and named ranges before editing anything
2. Put raw inputs, calculations, and outputs on separate sheets
3. Write formulas against named ranges rather than cell addresses
4. Add a checks row that must evaluate to zero when the model is consistent
5. Recalculate the whole workbook and confirm the checks row

## Success criteria

- Inputs, calculations and outputs are on separate sheets
- The consistency check row evaluates to zero
- No formula references a hard-coded literal that should be an input
