import pytest

from jobfit.config import load_skill_definitions
from jobfit.matching import SkillMatcher


@pytest.mark.parametrize(
    ("surface", "skill_id"),
    [
        ("C programming", "c"), ("C++", "cpp"), ("C#", "csharp"), ("F#", "fsharp"),
        (".NET", "dotnet"), ("ASP.NET", "aspnet"), ("Node.js", "nodejs"),
        ("CI/CD", "cicd"), ("Objective-C", "objective_c"), ("Power BI", "power_bi"),
    ],
)
def test_technical_punctuation(surface: str, skill_id: str) -> None:
    found = SkillMatcher(load_skill_definitions()).find(surface)
    assert skill_id in {item.skill_id for item in found}

