from skillforge.schema import ABSTAIN
from skillforge.synthesize import ABSTAIN_SIM_MAX, split_by_skill, synthesize
from skillforge.text import cosine, term_vector


def test_gold_is_always_on_the_menu_for_answerable_items(corpus):
    trajs, _ = synthesize(corpus, seed=1)
    for t in trajs:
        if t.gold_skill != ABSTAIN:
            assert t.gold_skill in t.menu


def test_abstain_items_contain_nothing_that_fits(corpus):
    by_name = {s["name"]: s for s in corpus}
    trajs, _ = synthesize(corpus, abstain_rate=1.0, seed=7)
    abstainers = [t for t in trajs if t.gold_skill == ABSTAIN]
    assert abstainers, "abstain_rate=1.0 produced no abstention items"
    for t in abstainers:
        origin = t.provenance["abstain_origin"]
        assert origin not in t.menu
        ov = term_vector(by_name[origin]["description"])
        for name in t.menu:
            assert cosine(ov, term_vector(by_name[name]["description"])) <= ABSTAIN_SIM_MAX


def test_every_distractor_is_typed(corpus):
    trajs, _ = synthesize(corpus, seed=3)
    for t in trajs:
        for name in t.menu:
            if name != t.gold_skill:
                assert t.distractor_kinds.get(name), f"untyped distractor {name}"


def test_synthesis_is_deterministic_under_a_seed(corpus):
    a, _ = synthesize(corpus, seed=42)
    b, _ = synthesize(corpus, seed=42)
    assert [t.to_dict() for t in a] == [t.to_dict() for t in b]


def test_a_different_seed_changes_the_menus(corpus):
    a, _ = synthesize(corpus, seed=1)
    b, _ = synthesize(corpus, seed=2)
    assert [t.menu for t in a] != [t.menu for t in b]


def test_holdout_shares_no_skill_between_splits(corpus):
    trajs, _ = synthesize(corpus, seed=11)
    train, dev = split_by_skill(trajs, 0.3, seed=11)
    assert train and dev
    ids = lambda rows: {t.provenance["skill_id"] for t in rows}  # noqa: E731
    assert not (ids(train) & ids(dev))


def test_plans_and_checks_are_never_fabricated(corpus):
    by_name = {s["name"]: s for s in corpus}
    trajs, _ = synthesize(corpus, seed=5)
    for t in trajs:
        if t.kind == "verify":
            assert t.gold_checks == by_name[t.gold_skill]["success_criteria"]
        if t.kind == "invoke":
            body = by_name[t.gold_skill]["body"]
            for step in t.gold_plan:
                assert step[:30] in body
