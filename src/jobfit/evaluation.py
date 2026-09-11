from __future__ import annotations

import re
from dataclasses import replace
from datetime import date
from decimal import Decimal

from jobfit.matching.taxonomy import Taxonomy
from jobfit.models import (
    AuthorizationHolding,
    CandidateProfile,
    ExpressionOp,
    LaborMarketAccess,
    MatchEvidence,
    MatchingMethod,
    MatchStatus,
    Requirement,
    RequirementResult,
    RequirementType,
    SkillState,
)
from jobfit.profile import completed_years

CEFR_RANK = {"A1": 1, "A2": 2, "B1": 3, "B2": 4, "C1": 5, "C2": 6}
LANGUAGE_PATTERNS = {
    "english": re.compile(r"\b(?:english|anglick\w*)\b", re.IGNORECASE),
    "czech": re.compile(r"\b(?:czech|češtin\w*|česk\w*)\b", re.IGNORECASE),
    "hebrew": re.compile(r"\b(?:hebrew|hebrej\w*)\b", re.IGNORECASE),
    "russian": re.compile(r"\b(?:russian|ruštin\w*|rusk\w*)\b", re.IGNORECASE),
    "french": re.compile(r"\b(?:french|francouz\w*)\b", re.IGNORECASE),
}


def _status(score: Decimal | None, optional: bool, review: bool = False) -> MatchStatus:
    if review:
        return MatchStatus.REVIEW
    if score is None:
        return MatchStatus.UNKNOWN
    if score >= 1:
        return MatchStatus.STRONG
    if score > 0:
        return MatchStatus.PARTIAL
    return MatchStatus.OPTIONAL_GAP if optional else MatchStatus.VERIFIED_GAP


def _legal_result(
    requirement: Requirement, profile: CandidateProfile, as_of: date
) -> tuple[RequirementResult, tuple[str, ...]] | None:
    folded = requirement.raw_text.casefold()
    legal_terms = (
        "work permit",
        "eligible to work",
        "right to work",
        "sponsorship",
        "visa",
        "residence permit",
        "residence authorization",
        "currently reside",
        "eu citizen",
        "eu citizenship",
    )
    if not any(term in folded for term in legal_terms):
        return None
    status = profile.legal_statuses.get("CZ")
    optional = requirement.requirement_type is RequirementType.PREFERRED
    base_evidence = MatchEvidence(
        skill_id=None,
        canonical_skill=None,
        matched_job_text=requirement.raw_text,
        candidate_level=None,
        required_level=None,
        requirement_type=requirement.requirement_type,
        matching_method=MatchingMethod.RULE,
        score=None,
        source_span=requirement.span,
    )
    if status is None:
        return (
            RequirementResult(
                requirement,
                MatchStatus.UNKNOWN,
                None,
                (base_evidence,),
                reason="No CZ legal status",
            ),
            (),
        )
    legal_evidence = replace(base_evidence, profile_evidence=status.evidence)
    if status.review_due_month and as_of.strftime("%Y-%m") >= status.review_due_month:
        return (
            RequirementResult(
                requirement,
                MatchStatus.REVIEW,
                None,
                (legal_evidence,),
                reason="Czech legal status has reached its review-due month",
            ),
            ("Czech legal facts require re-verification.",),
        )
    notes = (
        "Czech labour-market access: FREE_ACCESS; no work permit required.",
        "Residence authorization remains a separate requirement.",
    )
    mandatory = requirement.requirement_type is RequirementType.MANDATORY
    score: Decimal | None
    if "currently reside" in folded:
        score = Decimal(1) if profile.current_country == "CZ" else Decimal(0)
        return (
            RequirementResult(
                requirement,
                _status(score, optional),
                score,
                (replace(legal_evidence, score=score),),
                blocker=mandatory and score == 0,
                reason="Current profile country is not Czechia" if score == 0 else None,
            ),
            notes,
        )
    if "eu citizen" in folded or "eu citizenship" in folded:
        score = (
            Decimal(1)
            if any(item in {"EU", "CZ"} for item in profile.citizenship)
            else Decimal(0)
        )
        return (
            RequirementResult(
                requirement,
                _status(score, optional),
                score,
                (replace(legal_evidence, score=score),),
                blocker=mandatory and score == 0,
                reason="Profile verifies Israeli citizenship only",
            ),
            notes,
        )
    if ("sponsorship" in folded or "visa" in folded) and "work permit" not in folded:
        return (
            RequirementResult(
                requirement,
                MatchStatus.REVIEW,
                None,
                (legal_evidence,),
                reason="Sponsorship wording is ambiguous between work and residence status",
            ),
            notes,
        )
    if "residence permit" in folded or "residence authorization" in folded:
        if status.current_residence_authorization is AuthorizationHolding.HELD:
            score = Decimal(1)
        else:
            return (
                RequirementResult(
                    requirement,
                    MatchStatus.REVIEW,
                    None,
                    (legal_evidence,),
                    reason="Current Czech residence authorization is not verified",
                ),
                notes,
            )
    elif "eu work permit" in folded:
        return (
            RequirementResult(
                requirement,
                MatchStatus.REVIEW,
                None,
                (legal_evidence,),
                reason="EU work-permit wording requires recruiter confirmation despite free access",
            ),
            notes,
        )
    elif status.labor_market_access is LaborMarketAccess.FREE_ACCESS:
        score = Decimal(1)
    else:
        score = None
    return (
        RequirementResult(
            requirement,
            _status(score, optional),
            score,
            (replace(legal_evidence, score=score),),
            reason=(
                "Free Czech labour-market access satisfies work eligibility"
                if score == 1
                else "Work eligibility is unverified"
            ),
        ),
        notes,
    )


def _language_result(
    requirement: Requirement, profile: CandidateProfile
) -> RequirementResult | None:
    folded = requirement.raw_text.casefold()
    language = next(
        (name for name, pattern in LANGUAGE_PATTERNS.items() if pattern.search(folded)), None
    )
    if language is None:
        return None
    candidate = profile.languages.get(language)
    optional = requirement.requirement_type is RequirementType.PREFERRED
    score: Decimal | None = None
    reason: str | None = None
    blocker = False
    required_match = re.search(r"\b([abc][12])\b", requirement.raw_text, re.IGNORECASE)
    if candidate is None:
        reason = f"{language.title()} is not verified in the profile"
    elif required_match:
        required = required_match.group(1).upper()
        if candidate.cefr:
            score = min(
                Decimal(CEFR_RANK[candidate.cefr.upper()]) / Decimal(CEFR_RANK[required]),
                Decimal(1),
            )
            blocker = requirement.requirement_type is RequirementType.MANDATORY and score < 1
            reason = f"Verified {candidate.cefr}; vacancy requires {required}"
        else:
            reason = f"Profile level '{candidate.stated_level}' has no verified CEFR mapping"
    elif any(term in folded for term in ("fluent", "excellent", "very good", "velmi dobr")) and (
        candidate.stated_level.casefold() not in {"native", "fluent", "excellent"}
    ):
        reason = f"Profile states {candidate.stated_level}, not the requested verified level"
    else:
        score = Decimal(1)
        reason = f"Verified language level: {candidate.stated_level}"
    evidence = MatchEvidence(
        skill_id=f"language:{language}",
        canonical_skill=language.title(),
        matched_job_text=requirement.raw_text,
        candidate_level=(
            CEFR_RANK.get(candidate.cefr.upper()) if candidate and candidate.cefr else None
        ),
        required_level=(CEFR_RANK.get(required_match.group(1).upper()) if required_match else None),
        requirement_type=requirement.requirement_type,
        matching_method=MatchingMethod.RULE,
        score=score,
        source_span=requirement.span,
        profile_evidence=((reason,) if candidate else ()),
    )
    return RequirementResult(
        requirement=requirement,
        status=_status(score, optional),
        score=score,
        evidence=(evidence,),
        blocker=blocker,
        reason=reason,
    )


def _education_result(
    requirement: Requirement, profile: CandidateProfile, as_of: date
) -> RequirementResult | None:
    folded = requirement.raw_text.casefold()
    if not any(term in folded for term in ("bachelor", "master's degree", "masters degree")):
        return None
    equivalent = "equivalent experience" in folded or "or experience" in folded
    career_years = completed_years(profile.career_start, as_of)
    if equivalent and career_years >= 3:
        score = Decimal(1)
        reason = "Explicit equivalent-experience route is satisfied by verified career history"
    else:
        score = Decimal(0)
        reason = "Profile verifies a Practical Engineer credential, not the specified degree"
    optional = requirement.requirement_type is RequirementType.PREFERRED
    return RequirementResult(
        requirement,
        _status(score, optional),
        score,
        (
            MatchEvidence(
                None,
                "Education",
                requirement.raw_text,
                None,
                None,
                requirement.requirement_type,
                MatchingMethod.RULE,
                score,
                requirement.span,
                tuple(str(item) for item in profile.education),
            ),
        ),
        blocker=requirement.requirement_type is RequirementType.MANDATORY and score == 0,
        reason=reason,
    )


def _skill_atom(
    requirement: Requirement,
    mention_index: int,
    profile: CandidateProfile,
    taxonomy: Taxonomy,
    as_of: date,
) -> tuple[Decimal | None, MatchEvidence, SkillState]:
    mention = requirement.mentions[mention_index]
    candidate = profile.skills.get(mention.skill_id)
    taxonomy_text: str | None = None
    factor = Decimal(1)
    method = mention.method
    if candidate is None:
        inferred = taxonomy.infer(mention.skill_id, profile)
        if inferred:
            candidate, edge = inferred
            factor = edge.score_factor
            method = MatchingMethod.TAXONOMY
            taxonomy_text = (
                f"{edge.source} --{edge.relation}--> {edge.target} × {edge.score_factor}"
            )
    state = candidate.state if candidate else SkillState.UNKNOWN
    required_depth = requirement.required_depth
    score: Decimal | None
    if candidate is None or state is SkillState.UNKNOWN or candidate.depth is None:
        score = None
    elif state is SkillState.NONE:
        score = Decimal(0)
    elif required_depth is None or int(required_depth) == 0:
        score = factor
    else:
        score = (
            min(Decimal(int(candidate.depth)) / Decimal(int(required_depth)), Decimal(1))
            * factor
        )

    if requirement.minimum_years is not None and requirement.years_subject == "technology":
        years: Decimal | None = None
        if candidate:
            years = candidate.verified_years
            if years is None and candidate.experience_since:
                years = completed_years(candidate.experience_since, as_of)
        if years is None:
            score = None
        else:
            years_score = min(years / requirement.minimum_years, Decimal(1))
            score = years_score if score is None else min(score, years_score)

    evidence = MatchEvidence(
        skill_id=mention.skill_id,
        canonical_skill=mention.canonical_name,
        matched_job_text=mention.span.text,
        candidate_level=(
            int(candidate.depth) if candidate and candidate.depth is not None else None
        ),
        required_level=(int(required_depth) if required_depth is not None else None),
        requirement_type=requirement.requirement_type,
        matching_method=method,
        score=score,
        source_span=mention.span,
        profile_evidence=candidate.evidence if candidate else (),
        taxonomy_inference=taxonomy_text,
    )
    return score, evidence, state


def evaluate_requirement(
    requirement: Requirement,
    profile: CandidateProfile,
    taxonomy: Taxonomy,
    as_of: date,
) -> tuple[RequirementResult, tuple[str, ...]]:
    optional = requirement.requirement_type is RequirementType.PREFERRED
    legal = _legal_result(requirement, profile, as_of)
    if legal is not None:
        return legal
    language = _language_result(requirement, profile)
    if language is not None:
        return language, ()
    education = _education_result(requirement, profile, as_of)
    if education is not None:
        return education, ()
    if requirement.expression_op is ExpressionOp.REVIEW:
        return (
            RequirementResult(
                requirement,
                MatchStatus.REVIEW,
                None,
                (),
                reason=requirement.review_reason,
            ),
            (),
        )

    atom_values: list[Decimal | None] = []
    evidence: list[MatchEvidence] = []
    states: list[SkillState] = []
    for index in range(len(requirement.mentions)):
        value, item_evidence, state = _skill_atom(requirement, index, profile, taxonomy, as_of)
        atom_values.append(value)
        evidence.append(item_evidence)
        states.append(state)

    if requirement.minimum_years is not None and (
        requirement.years_subject == "overall" or not requirement.mentions
    ):
        years = completed_years(profile.career_start, as_of)
        value = min(years / requirement.minimum_years, Decimal(1))
        atom_values.append(value)
        evidence.append(
            MatchEvidence(
                None,
                "Overall software-development experience",
                requirement.raw_text,
                None,
                None,
                requirement.requirement_type,
                MatchingMethod.RULE,
                value,
                requirement.span,
                (f"Professional development since {profile.career_start}.",),
            )
        )

    known = [value for value in atom_values if value is not None]
    unknown_count = len(atom_values) - len(known)
    score: Decimal | None
    if not atom_values:
        score = None
    elif requirement.expression_op is ExpressionOp.ANY:
        if known and max(known) >= 1:
            score = Decimal(1)
        elif unknown_count:
            score = None
        else:
            score = max(known)
    elif requirement.expression_op is ExpressionOp.ALL:
        if known and min(known) == 0:
            score = Decimal(0)
        elif unknown_count:
            score = None
        else:
            score = sum(known, Decimal(0)) / Decimal(len(known))
    elif requirement.expression_op is ExpressionOp.COMPOSITE:
        score = sum(known, Decimal(0)) / Decimal(len(atom_values))
    elif unknown_count:
        score = None
    elif known:
        score = sum(known, Decimal(0)) / Decimal(len(known))
    else:
        score = None

    verified_none = bool(states) and all(state is SkillState.NONE for state in states)
    blocker = (
        requirement.requirement_type is RequirementType.MANDATORY
        and (
            verified_none
            or (
                requirement.minimum_years is not None
                and score is not None
                and score < 1
            )
        )
    )
    reason = None
    if score is None:
        reason = "Profile evidence is incomplete for this requirement"
    elif verified_none:
        reason = "Required capability is explicitly recorded as NONE"
    return (
        RequirementResult(
            requirement=requirement,
            status=_status(score, optional),
            score=score,
            evidence=tuple(evidence),
            blocker=blocker,
            reason=reason,
        ),
        (),
    )


def evaluate_requirements(
    requirements: tuple[Requirement, ...],
    profile: CandidateProfile,
    taxonomy: Taxonomy,
    as_of: date,
) -> tuple[tuple[RequirementResult, ...], tuple[str, ...]]:
    results: list[RequirementResult] = []
    legal_notes: list[str] = []
    for requirement in requirements:
        result, notes = evaluate_requirement(requirement, profile, taxonomy, as_of)
        results.append(result)
        legal_notes.extend(notes)
    return tuple(results), tuple(dict.fromkeys(legal_notes))
