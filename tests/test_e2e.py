from datetime import date
from pathlib import Path

from conftest import fixture_path

from jobfit.models import Decision, EvaluationRequest
from jobfit.pipeline import evaluate_job


def test_end_to_end_saved_html() -> None:
    result = evaluate_job(EvaluationRequest(
        "https://www.linkedin.com/jobs/view/4462925691",
        Path("profiles/master_profile.yaml"),
        html_path=fixture_path("jobs/linkedin_jsonld.html"), as_of=date(2026, 9, 11)
    ))
    assert result.job.company == "Example Labs"
    assert result.fit_score is not None
    assert result.decision in set(Decision)
