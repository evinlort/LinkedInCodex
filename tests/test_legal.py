from datetime import date
from pathlib import Path

from jobfit.models import EvaluationRequest, MatchStatus
from jobfit.pipeline import evaluate_job


def _run(tmp_path: Path, line: str, as_of: date = date(2026, 9, 11)):
    path = tmp_path / "job.txt"
    path.write_text(f"Requirements:\n- {line}\n", encoding="utf-8")
    return evaluate_job(EvaluationRequest(
        "https://www.linkedin.com/jobs/view/4462925691",
        Path("profiles/master_profile.yaml"), text_path=path, as_of=as_of
    ))


def test_free_access_satisfies_work_eligibility(tmp_path: Path) -> None:
    result = _run(tmp_path, "Candidate must be eligible to work in Czechia")
    assert result.requirements[0].status is MatchStatus.STRONG
    assert result.requirements[0].evidence[0].score == 1
    assert result.requirements[0].evidence[0].profile_evidence
    assert not result.blockers


def test_residence_and_sponsorship_are_not_guessed(tmp_path: Path) -> None:
    result = _run(tmp_path, "No visa sponsorship available")
    assert result.requirements[0].status is MatchStatus.REVIEW


def test_stale_legal_fact_requires_review(tmp_path: Path) -> None:
    result = _run(tmp_path, "Right to work in Czechia", date(2027, 3, 1))
    assert result.requirements[0].status is MatchStatus.REVIEW


def test_current_czech_residence_requirement_is_blocker(tmp_path: Path) -> None:
    result = _run(tmp_path, "Candidate must currently reside in Czechia")
    assert result.requirements[0].status is MatchStatus.VERIFIED_GAP
    assert result.blockers


def test_mandatory_czech_c1_is_blocker(tmp_path: Path) -> None:
    result = _run(tmp_path, "Czech C1")
    assert result.requirements[0].status is MatchStatus.PARTIAL
    assert result.blockers


def test_czech_high_english_level_needs_review(tmp_path: Path) -> None:
    result = _run(tmp_path, "Velmi dobrou znalost anglického jazyka")
    assert result.requirements[0].status is MatchStatus.UNKNOWN
    assert result.requirements[0].reason == (
        "Profile states working proficiency, not the requested verified level"
    )
