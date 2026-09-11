from jobfit.config import load_skill_definitions
from jobfit.matching import SkillMatcher
from jobfit.models import MatchingMethod


def test_ambiguity_context() -> None:
    matcher = SkillMatcher(load_skill_definitions())
    assert {item.skill_id for item in matcher.find("Go developer")} == {"go"}
    assert "go" not in {item.skill_id for item in matcher.find("ready to go live")}
    assert {item.skill_id for item in matcher.find("Git experience")} == {"git"}
    assert not matcher.find("Get the data")


def test_multiword_and_fuzzy_fallback() -> None:
    matcher = SkillMatcher(load_skill_definitions())
    assert "gitlab_ci" in {item.skill_id for item in matcher.find("GitLab CI experience")}
    fuzzy = matcher.find("PostgreSQLl")
    assert fuzzy and fuzzy[0].method is MatchingMethod.FUZZY
