from __future__ import annotations

from dataclasses import replace
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from jobfit.config import EngineConfig
from jobfit.models import (
    ComponentResult,
    Decision,
    FitResult,
    JobPosting,
    MatchStatus,
    RequirementResult,
    RequirementType,
    ScoreComponent,
)


def _round(value: Decimal) -> int:
    return int(value.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _average(values: list[Decimal], default: Decimal = Decimal(1)) -> Decimal:
    return sum(values, Decimal(0)) / Decimal(len(values)) if values else default


def score_fit(
    job: JobPosting,
    results: tuple[RequirementResult, ...],
    config: EngineConfig,
    as_of: date,
    section_quality: Decimal,
    legal_notes: tuple[str, ...],
    diagnostics: tuple[str, ...] = (),
) -> FitResult:
    components: list[ComponentResult] = []
    weighted_total = Decimal(0)
    active_weight = Decimal(0)
    for component in ScoreComponent:
        relevant = [item for item in results if item.requirement.component is component]
        known = [item.score for item in relevant if item.score is not None]
        weight = config.component_weights[component]
        # UNKNOWN is not a verified gap, but it also is not proof of a fit.
        # Give points only for requirements supported by profile evidence.
        ratio = sum(known, Decimal(0)) / Decimal(len(relevant)) if relevant else None
        awarded = weight * ratio if ratio is not None else None
        if awarded is not None:
            weighted_total += awarded
            active_weight += weight
        components.append(
            ComponentResult(
                component=component,
                maximum_weight=weight,
                ratio=ratio,
                awarded_points=awarded,
                determined_count=len(known),
                unknown_count=len(relevant) - len(known),
            )
        )
    fit_score = _round(Decimal(100) * weighted_total / active_weight) if active_weight else None
    essential_components = {
        ScoreComponent.MANDATORY_ROLE,
        ScoreComponent.CORE_RESPONSIBILITIES,
    }
    has_essential_requirements = any(
        item.requirement.component in essential_components for item in results
    )
    if not has_essential_requirements:
        fit_score = None
        diagnostics = (
            *diagnostics,
            "No mandatory technical or core responsibility requirements were found",
        )
    requirements_by_component = {
        component.component: component.determined_count + component.unknown_count
        for component in components
    }
    scored_results = tuple(
        replace(
            item,
            score_contribution=(
                Decimal(100)
                * config.component_weights[item.requirement.component]
                / active_weight
                * item.score
                / Decimal(requirements_by_component[item.requirement.component])
                if item.score is not None and active_weight
                else None
            ),
        )
        for item in results
    )

    mandatory = [
        item for item in results if item.requirement.requirement_type is RequirementType.MANDATORY
    ]
    mandatory_coverage = (
        Decimal(sum(item.score is not None for item in mandatory)) / Decimal(len(mandatory))
        if mandatory
        else Decimal(1)
    )
    overall_coverage = (
        Decimal(sum(item.score is not None for item in results)) / Decimal(len(results))
        if results
        else Decimal(0)
    )
    parser_certainty = _average([item.requirement.parser_confidence for item in results])
    evidence_methods = [
        evidence.matching_method.value for item in results for evidence in item.evidence
    ]
    matcher_certainty = _average(
        [config.matcher_quality.get(method, Decimal(0)) for method in evidence_methods]
    )
    cw = config.confidence_weights
    confidence = _round(
        Decimal(100)
        * (
            cw["mandatory_coverage"] * mandatory_coverage
            + cw["overall_coverage"] * overall_coverage
            + cw["parser_certainty"] * parser_certainty
            + cw["section_quality"] * section_quality
            + cw["matcher_quality"] * matcher_certainty
        )
    )

    blockers = tuple(
        item.reason or item.requirement.raw_text for item in results if item.blocker
    )
    unresolved_gate = any(
        item.requirement.requirement_type is RequirementType.MANDATORY
        and item.status in {MatchStatus.UNKNOWN, MatchStatus.REVIEW}
        for item in results
    ) or any(item.status is MatchStatus.REVIEW for item in results)
    thresholds = config.decision_thresholds
    if blockers:
        decision = Decision.DO_NOT_APPLY
    elif (
        fit_score is None
        or confidence < thresholds["manual_review_confidence"]
        or unresolved_gate
    ):
        decision = Decision.MANUAL_REVIEW
    elif fit_score >= thresholds["excellent"]:
        decision = Decision.EXCELLENT_FIT
    elif fit_score >= thresholds["good"]:
        decision = Decision.GOOD_FIT
    elif fit_score >= thresholds["borderline"]:
        decision = Decision.BORDERLINE
    elif fit_score >= thresholds["weak"]:
        decision = Decision.WEAK_FIT
    else:
        decision = Decision.DO_NOT_APPLY

    return FitResult(
        schema_version="1.0",
        job=job,
        evaluated_as_of=as_of,
        fit_score=fit_score,
        confidence_score=confidence,
        decision=decision,
        requirements=scored_results,
        components=tuple(components),
        blockers=blockers,
        legal_notes=legal_notes,
        diagnostics=diagnostics,
    )
