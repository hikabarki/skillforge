import pytest

from skillforge.frontmatter import FrontmatterError, parse


def test_scalars_lists_and_body():
    meta, body = parse(
        "---\nname: docx-report\ndescription: \"Use when: a doc is needed\"\n"
        "allowed-tools: [Read, Write]\ntags:\n  - office\n  - writing\n---\n\n# Body\ntext\n"
    )
    assert meta["name"] == "docx-report"
    assert meta["description"] == "Use when: a doc is needed"
    assert meta["allowed-tools"] == ["Read", "Write"]
    assert meta["tags"] == ["office", "writing"]
    assert body.startswith("# Body")


def test_crlf_and_bom_are_tolerated():
    meta, _ = parse("﻿---\r\nname: x\r\ndescription: y\r\n---\r\n\r\nbody\r\n")
    assert meta == {"name": "x", "description": "y"}


@pytest.mark.parametrize(
    "text",
    [
        "# no frontmatter\n",
        "---\nname: x\n",                       # never closed
        "---\nnot-a-mapping\n---\nbody\n",
        "---\nname: x\ndescription: |\n---\nbody\n",  # block scalar
    ],
)
def test_unsupported_shapes_raise_rather_than_guess(text):
    with pytest.raises(FrontmatterError):
        parse(text)


def test_nested_mapping_is_refused_loudly():
    with pytest.raises(FrontmatterError, match="nested mappings"):
        parse("---\nname: x\nmeta:\n  version: 1\n---\nbody\n")
