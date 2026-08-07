import pathlib

import pytest


@pytest.fixture(scope="session")
def fixtures_root() -> pathlib.Path:
    return pathlib.Path(__file__).resolve().parents[1] / "fixtures" / "skills"


@pytest.fixture(scope="session")
def corpus(fixtures_root):
    from skillforge.harvest import harvest

    skills, _ = harvest(str(fixtures_root))
    return [s.to_dict() for s in skills]
