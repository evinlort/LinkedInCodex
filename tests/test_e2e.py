from datetime import date
from pathlib import Path

from conftest import fixture_path

from jobfit.models import Decision, EvaluationRequest, MatchStatus, RequirementType
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


def test_non_python_backend_role_does_not_get_full_fit(tmp_path: Path) -> None:
    job_text = tmp_path / "crypto_backend.txt"
    job_text.write_text(
        "💪 What You’ll Be Working On\n"
        "- Build crypto backend services\n"
        "💪 About You\n"
        "- You have production experience in TypeScript/Node.js or Go\n"
        "- Solid knowledge of PostgreSQL\n"
        "Nice to have:\n"
        "- Docker\n"
        "✍️ Our Stack\n"
        "TypeScript, Node.js, Go, PostgreSQL, Docker\n"
        "What We Offer\n"
        "Flexible working hours\n",
        encoding="utf-8",
    )

    result = evaluate_job(
        EvaluationRequest(
            "4466312487",
            Path("profiles/master_profile.yaml"),
            text_path=job_text,
            as_of=date(2026, 9, 12),
        )
    )

    stack = next(
        item
        for item in result.requirements
        if "TypeScript/Node.js or Go" in item.requirement.raw_text
    )
    assert result.fit_score is not None
    assert result.fit_score < 100
    assert result.decision is Decision.MANUAL_REVIEW
    assert stack.requirement.requirement_type is RequirementType.MANDATORY
    assert stack.status is MatchStatus.UNKNOWN
