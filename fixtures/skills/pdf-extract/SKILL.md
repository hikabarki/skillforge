---
name: pdf-extract
description: Use this skill for anything involving a PDF file — extracting text or tables, merging or splitting documents, rotating pages, filling forms, adding watermarks, or running OCR over a scanned document to make it searchable. Triggers include '.pdf', 'merge these pdfs', 'pull the tables out'.
license: Apache-2.0
allowed-tools: [Read, Write, Bash]
---

# PDF toolkit

## Instructions

1. Determine whether the PDF carries a text layer before choosing a path
2. For scanned documents, run OCR first and keep the OCR output separately
3. Extract tables page by page and check each against the rendered page
4. Preserve the original file; write every result to a new path

## Success criteria

- Extracted table row counts match the rendered page
- Scanned inputs produce a searchable output, not an image-only copy
- The source PDF is byte-identical after the run
