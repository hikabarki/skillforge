import pytest

from skillforge.evaluate import BASELINES, parse_prediction, score
from skillforge.render import build_prompt, build_target
from skillforge.schema import ABSTAIN
from skillforge.synthesize import synthesize


@pytest.fixture(scope="module")
def scored(corpus):
    trajs = [t.to_dict() for t in synthesize(corpus, seed=13)[0]]
    by_name = {s["name"]: s for s in corpus}
    return trajs, by_name


@pytest.mark.parametrize(
    "text,expected",
    [
        ("skill: docx-report", "docx-report"),
        ("  Skill = pdf-extract  ", "pdf-extract"),
        ("skill: none", ABSTAIN),
        ("I think you should use docx-report", None),
    ],
)
def test_prediction_parsing(text, expected):
    assert parse_prediction(text)[0] == expected


def test_parse_pulls_the_plan_after_the_skill_line():
    name, steps = parse_prediction("skill: x\nplan:\n1. first thing\n2. second thing")
    assert name == "x" and steps == ["first thing", "second thing"]


def test_oracle_scores_one_and_therefore_the_scorer_agrees_with_the_labels(scored):
    trajs, by_name = scored
    predict = BASELINES["oracle"](by_name)
    report = score(trajs, {t["trajectory_id"]: predict(t) for t in trajs}, by_name)
    assert report["accuracy"] == 1.0
    assert report["abstention"]["false_invocation_rate"] == 0.0


def test_always_abstain_gets_exactly_the_abstain_items(scored):
    trajs, by_name = scored
    predict = BASELINES["always_abstain"](by_name)
    report = score(trajs, {t["trajectory_id"]: predict(t) for t in trajs}, by_name)
    assert report["abstention"]["recall"] == 1.0
    assert report["answerable"]["accuracy"] == 0.0


def test_undefined_rates_are_none_not_zero(scored):
    trajs, by_name = scored
    answerable = [t for t in trajs if t["gold_skill"] != ABSTAIN]
    predict = BASELINES["oracle"](by_name)
    report = score(answerable, {t["trajectory_id"]: predict(t) for t in answerable}, by_name)
    assert report["abstention"]["n"] == 0
    assert report["abstention"]["recall"] is None


def test_target_is_reachable_from_the_prompt(scored):
    trajs, by_name = scored
    for t in trajs:
        prompt, target = build_prompt(t, by_name), build_target(t)
        name = parse_prediction(target)[0]
        assert name is not None
        if name != ABSTAIN:
            assert f"- {name}:" in prompt, "gold skill is not on the rendered menu"


def test_missing_predictions_are_counted_not_scored_as_wrong(scored):
    trajs, by_name = scored
    report = score(trajs, {}, by_name)
    assert report["n_scored"] == 0 and report["n_missing_predictions"] == len(trajs)
