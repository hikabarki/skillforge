"""A deliberately small YAML-frontmatter reader.

Why not PyYAML: the core pipeline is stdlib-only so it runs anywhere, and SKILL.md
frontmatter in the wild uses a tiny subset of YAML. The parser below handles exactly
that subset and *raises* on anything else rather than guessing. A silently
mis-parsed `description` would corrupt the trigger surface the whole dataset is
built on, so failing loudly is the cheaper error.

Supported:
    key: scalar
    key: "quoted scalar with: colons"
    key: [a, b, c]
    key:
      - a
      - b
"""

from __future__ import annotations

from typing import Any

DELIM = "---"


class FrontmatterError(ValueError):
    """Raised when frontmatter is absent or uses YAML this reader will not guess at."""


def _scalar(raw: str) -> Any:
    raw = raw.strip()
    if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in "\"'":
        return raw[1:-1]
    if raw in ("true", "True"):
        return True
    if raw in ("false", "False"):
        return False
    if raw in ("null", "~", ""):
        return None
    return raw


def _inline_list(raw: str) -> list[Any]:
    inner = raw.strip()[1:-1].strip()
    if not inner:
        return []
    return [_scalar(part) for part in inner.split(",")]


def split(text: str) -> tuple[str, str]:
    """Return (frontmatter_block, body). Raises if the document has no frontmatter."""
    normalized = text.replace("\r\n", "\n").lstrip("﻿")
    if not normalized.startswith(DELIM):
        raise FrontmatterError("document does not start with a '---' frontmatter delimiter")
    end = normalized.find(f"\n{DELIM}", len(DELIM))
    if end == -1:
        raise FrontmatterError("frontmatter opened with '---' but never closed")
    block = normalized[len(DELIM) : end]
    rest = normalized[end + len(DELIM) + 1 :]
    return block.strip("\n"), rest.lstrip("\n")


def parse(text: str) -> tuple[dict[str, Any], str]:
    block, body = split(text)
    data: dict[str, Any] = {}
    pending_key: str | None = None

    for lineno, line in enumerate(block.split("\n"), 1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue

        stripped = line.strip()

        if stripped.startswith("- "):
            if pending_key is None:
                raise FrontmatterError(f"line {lineno}: list item with no key above it")
            data.setdefault(pending_key, []).append(_scalar(stripped[2:]))
            continue

        if line[0] in " \t":
            raise FrontmatterError(
                f"line {lineno}: nested mappings are not supported by this reader — "
                f"flatten the frontmatter or open an issue ({stripped!r})"
            )

        if ":" not in stripped:
            raise FrontmatterError(f"line {lineno}: expected 'key: value', got {stripped!r}")

        key, _, value = stripped.partition(":")
        key = key.strip()
        value = value.strip()

        if not value:
            data[key] = []
            pending_key = key
            continue

        pending_key = None
        if value.startswith("[") and value.endswith("]"):
            data[key] = _inline_list(value)
        elif value in ("|", ">"):
            raise FrontmatterError(
                f"line {lineno}: block scalars ('{value}') are not supported — "
                "put long text in the body, not the frontmatter"
            )
        else:
            data[key] = _scalar(value)

    return data, body
