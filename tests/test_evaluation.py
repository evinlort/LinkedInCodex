from datetime import date
from pathlib import Path

from conftest import fixture_path

from jobfit.models import EvaluationRequest, MatchStatus
from jobfit.pipeline import evaluate_job


def test_none_unknown_and_partial_are_distinct() -> None:
    result = evaluate_job(
        EvaluationRequest(
            "https://www.linkedin.com/jobs/view/4462925691",
            Path("profiles/master_profile.yaml"),
            text_path=fixture_path("jobs/english_backend.txt"),
            as_of=date(2026, 9, 11),
        )
    )
    by_skill = {
        evidence.skill_id: item
        for item in result.requirements
        for evidence in item.evidence
        if evidence.skill_id
    }
    assert by_skill["python"].status is MatchStatus.STRONG
    assert by_skill["docker"].status is MatchStatus.PARTIAL
    assert by_skill["cpp"].status is MatchStatus.OPTIONAL_GAP

