---
name: docx-report
description: Use this skill when the user wants to produce or edit a Word document — reports, memos, letters, or templates with headings, tables of contents, page numbers and letterheads. Triggers include 'word doc', '.docx', '.dotx', or a request to turn notes into a formatted report. Do not use for PDFs or spreadsheets.
license: Apache-2.0
allowed-tools: [Read, Write, Bash]
---

# Word report builder

## Instructions

1. Read the source material and list every section the document needs
2. Choose a template from `templates/` matching the requested tone
3. Populate the template section by section, never all at once
4. Regenerate the table of contents after the last section lands
5. Convert to .docx and open it once to confirm pagination

## Success criteria

- Every heading level is styled from the template, not hand-formatted
- The table of contents matches the final heading order
- No placeholder text of the form `TODO` or `<...>` survives
