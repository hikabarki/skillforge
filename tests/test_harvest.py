import pytest

from skillforge.harvest import extract_success_criteria, harvest, normalize

GOOD = (
    "---\nname: demo-skill\ndescription: Use this skill when the user wants to demo things.\n"
    "license: Apache-2.0\n---\n\n## Instructions\n\n1. Do the thing\n2. Check the thing\n\n"
    "## Success criteria\n\n- The thing is done\n- Nothing else broke\n"
)


def test_normalize_populates_the_contract():
    s = normalize(GOOD, source="fixtures", rel_path="demo/SKILL.md")
    assert s.skill_id == "fixtures/demo-skill"
    assert s.license == "Apache-2.0"
    assert s.success_criteria == ["The thing is done", "Nothing else broke"]
    assert len(s.body_sha256) == 64 and s.body_chars > 0
    assert s.warnings == []


def test_missing_description_is_rejected_not_invented():
    with pytest.raises(ValueError, match="trigger surface"):
        normalize("---\nname: x\n---\nbody\n", source="f", rel_path="x/SKILL.md")


def test_warnings_flag_smells_without_dropping_the_skill():
    text = GOOD.replace("name: demo-skill", "name: Demo Skill").replace("license: Apache-2.0\n", "")
    s = normalize(text, source="f", rel_path="x/SKILL.md")
    assert any("slug" in w for w in s.warnings)
    assert any("license" in w for w in s.warnings)


def test_criteria_capture_stops_at_the_next_heading():
    body = "## Success criteria\n- a\n- b\n\n## Notes\n- not a criterion\n"
    assert extract_success_criteria(body) == ["a", "b"]


def test_fixture_corpus_round_trips(fixtures_root):
    skills, rejects = harvest(str(fixtures_root))
    assert len(skills) >= 10
    assert {r["path"].split("/")[0] for r in rejects} == {
        "_broken-no-frontmatter",
        "_broken-no-description",
    }
    assert all(s.description and s.success_criteria for s in skills)


def test_duplicate_names_within_a_source_are_rejected(tmp_path):
    for sub in ("a", "b"):
        d = tmp_path / sub
        d.mkdir()
        (d / "SKILL.md").write_text(GOOD, encoding="utf-8")
    skills, rejects = harvest(str(tmp_path), source="dup")
    assert len(skills) == 1
    assert "duplicate skill_id" in rejects[0]["reason"]
