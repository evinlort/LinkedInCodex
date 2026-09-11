from datetime import date
from decimal import Decimal

from jobfit.config import load_engine_config
from jobfit.models import (
    ExpressionOp,
    JobPosting,
    MatchStatus,
    Requirement,
    RequirementResult,
    RequirementType,
    ScoreComponent,
    SourceSpan,
)
from jobfit.scoring import score_fit


def _result(score: Decimal | None, blocker: bool = False) -> RequirementResult:
    req = Requirement("r", "Python", SourceSpan(0, 6, "Python"), "Requirements",
                      RequirementType.MANDATORY, ScoreComponent.MANDATORY_ROLE,
                      ExpressionOp.ATOM, None, None, None, Decimal(1))
    status = (
        MatchStatus.UNKNOWN
        if score is None
        else (MatchStatus.STRONG if score == 1 else MatchStatus.VERIFIED_GAP)
    )
    return RequirementResult(req, status, score, (), blocker, "blocker" if blocker else None)


def test_blocker_overrides_high_score() -> None:
    job = JobPosting("linkedin", "1", "url", None, None, None, None, None, "Python", "h")
    result = score_fit(job, (_result(Decimal(1), True),), load_engine_config(),
                       date(2026, 9, 11), Decimal(1), ())
    assert result.fit_score == 100
    assert result.requirements[0].score_contribution == 100
    assert result.decision.value == "DO_NOT_APPLY"


def test_unknown_reduces_confidence_and_gets_no_fit_points() -> None:
    job = JobPosting("linkedin", "1", "url", None, None, None, None, None, "Python", "h")
    result = score_fit(job, (_result(Decimal(1)), _result(None)), load_engine_config(),
                       date(2026, 9, 11), Decimal(1), ())
    assert result.fit_score == 50
    assert result.confidence_score < 100


def test_seniority_alone_cannot_make_a_full_fit() -> None:
    job = JobPosting("linkedin", "1", "url", None, None, None, None, None, "3 years", "h")
    req = Requirement(
        "r",
        "3 years",
        SourceSpan(0, 7, "3 years"),
        "Requirements",
        RequirementType.MANDATORY,
        ScoreComponent.SENIORITY,
        ExpressionOp.ATOM,
        None,
        Decimal(3),
        "overall",
        Decimal(1),
    )
    known = RequirementResult(req, MatchStatus.STRONG, Decimal(1), ())

    result = score_fit(
        job,
        (known,),
        load_engine_config(),
        date(2026, 9, 11),
        Decimal(1),
        (),
    )

    assert result.fit_score is None
    assert result.decision.value == "MANUAL_REVIEW"
    assert result.diagnostics == (
        "No mandatory technical or core responsibility requirements were found",
    )
