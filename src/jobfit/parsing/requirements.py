from __future__ import annotations

import re
import unicodedata
from dataclasses import replace
from decimal import Decimal

from jobfit.config import load_requirement_rules, load_sections
from jobfit.models import (
    ExpressionOp,
    JobPosting,
    Requirement,
    RequirementType,
    ScoreComponent,
    SkillDepth,
    SourceSpan,
)

YEAR_RE = re.compile(
    r"(?i)(?:minimum\s+|at\s+least\s+|minimálně\s+)?(\d+(?:\.\d+)?)\s*\+?\s*"
    r"(?:years?|yrs?|let|roky|roků)"
)
BULLET_RE = re.compile(r"^(?:[-*•‣▪◦]+|\d+[.)])\s*")
LEGAL_TERMS = (
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
LANGUAGE_PATTERNS = {
    "english": re.compile(r"\b(?:english|anglick\w*)\b", re.IGNORECASE),
    "czech": re.compile(r"\b(?:czech|češtin\w*|česk\w*)\b", re.IGNORECASE),
    "hebrew": re.compile(r"\b(?:hebrew|hebrej\w*)\b", re.IGNORECASE),
    "russian": re.compile(r"\b(?:russian|ruštin\w*|rusk\w*)\b", re.IGNORECASE),
    "french": re.compile(r"\b(?:french|francouz\w*)\b", re.IGNORECASE),
}


def _key(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text)
    normalized = normalized.replace("’", "'").replace("‘", "'")
    normalized = re.sub(r"^[^\w]+", "", normalized)
    return normalized.strip().rstrip(":?!").casefold()


def _component(req_type: RequirementType, text: str) -> ScoreComponent:
    folded = text.casefold()
    if any(term in folded for term in LEGAL_TERMS) or any(
        pattern.search(text) for pattern in LANGUAGE_PATTERNS.values()
    ):
        return ScoreComponent.COMPATIBILITY
    if YEAR_RE.search(text) or any(
        term in folded for term in ("senior", "ownership", "architect", "degree")
    ):
        return ScoreComponent.SENIORITY
    if req_type is RequirementType.CORE_RESPONSIBILITY:
        return ScoreComponent.CORE_RESPONSIBILITIES
    if req_type is RequirementType.PREFERRED:
        return ScoreComponent.PREFERRED
    return ScoreComponent.MANDATORY_ROLE


def parse_requirements(job: JobPosting) -> tuple[tuple[Requirement, ...], Decimal]:
    sections = load_sections()
    rules = load_requirement_rules()
    section_lookup: dict[str, RequirementType] = {}
    type_map = {
        "mandatory": RequirementType.MANDATORY,
        "core_responsibility": RequirementType.CORE_RESPONSIBILITY,
        "preferred": RequirementType.PREFERRED,
        "context": RequirementType.CONTEXT,
        "benefits": RequirementType.CONTEXT,
    }
    for group, headings in sections.items():
        for heading in headings:
            section_lookup[_key(heading)] = type_map[group]

    current_type: RequirementType | None = None
    current_section: str | None = None
    recognized_heading = False
    requirements: list[Requirement] = []
    offset = 0
    for source_line in job.raw_description.splitlines(keepends=True):
        raw_without_newline = source_line.rstrip("\r\n")
        stripped = raw_without_newline.strip()
        leading = len(raw_without_newline) - len(raw_without_newline.lstrip())
        if not stripped:
            offset += len(source_line)
            continue
        if any(str(term).casefold() in stripped.casefold() for term in rules["stop_terms"]):
            current_type = None
            current_section = None
            offset += len(source_line)
            continue
        heading_type = section_lookup.get(_key(stripped))
        if heading_type is not None:
            current_type = heading_type
            current_section = stripped.rstrip(":")
            recognized_heading = True
            offset += len(source_line)
            continue

        bullet = BULLET_RE.match(stripped)
        clean = stripped[bullet.end() :] if bullet else stripped
        clean_key = clean.casefold()
        inline_preferred = any(term in clean_key for term in rules["preferred_terms"])
        inline_mandatory = any(term in clean_key for term in rules["mandatory_terms"])
        req_type = current_type
        if req_type is RequirementType.PREFERRED or inline_preferred:
            req_type = RequirementType.PREFERRED
        elif req_type is None and inline_mandatory:
            req_type = RequirementType.MANDATORY
        if req_type is None or req_type is RequirementType.CONTEXT:
            offset += len(source_line)
            continue

        depth: SkillDepth | None = None
        for depth_name, terms in rules["depth_terms"].items():
            if any(str(term).casefold() in clean_key for term in terms):
                depth = SkillDepth[depth_name]
                break
        if depth is None:
            depth = (
                SkillDepth.EXPOSURE
                if req_type is RequirementType.PREFERRED
                else SkillDepth.WORKING
            )
        year_match = YEAR_RE.search(clean)
        minimum_years = Decimal(year_match.group(1)) if year_match else None
        years_subject = None
        if year_match:
            years_subject = (
                "overall"
                if any(
                    term in clean_key
                    for term in (
                        "software",
                        "developer",
                        "development",
                        "engineering",
                        "programming",
                    )
                )
                else "technology"
            )

        clean_position = raw_without_newline.find(clean, leading)
        start = offset + max(clean_position, 0)
        span = SourceSpan(start=start, end=start + len(clean), text=clean)
        parser_confidence = Decimal("1.0") if current_type is not None else Decimal("0.75")
        requirements.append(
            Requirement(
                id=f"req-{len(requirements) + 1:03d}",
                raw_text=clean,
                span=span,
                section=current_section,
                requirement_type=req_type,
                component=_component(req_type, clean),
                expression_op=ExpressionOp.ATOM,
                required_depth=depth,
                minimum_years=minimum_years,
                years_subject=years_subject,
                parser_confidence=parser_confidence,
            )
        )
        offset += len(source_line)

    if recognized_heading:
        section_quality = Decimal("1.0")
    elif requirements:
        section_quality = Decimal("0.7")
    else:
        section_quality = Decimal("0.5")
    return tuple(requirements), section_quality


def _benefits(text: str) -> tuple[str, ...]:
    sections = load_sections()
    rules = load_requirement_rules()
    all_headings = {_key(item) for values in sections.values() for item in values}
    benefit_headings = {_key(item) for item in sections["benefits"]}
    inside_benefits = False
    result: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if any(str(term).casefold() in stripped.casefold() for term in rules["stop_terms"]):
            inside_benefits = False
            continue
        line_key = _key(stripped)
        if line_key in all_headings:
            inside_benefits = line_key in benefit_headings
            continue
        if inside_benefits:
            bullet = BULLET_RE.match(stripped)
            result.append(stripped[bullet.end() :] if bullet else stripped)
    return tuple(result)


def structure_job(job: JobPosting, requirements: tuple[Requirement, ...]) -> JobPosting:
    """Attach deterministic section output while retaining the exact source text."""
    return replace(
        job,
        responsibilities=tuple(
            item.raw_text
            for item in requirements
            if item.requirement_type is RequirementType.CORE_RESPONSIBILITY
        ),
        mandatory_requirements=tuple(
            item.raw_text
            for item in requirements
            if item.requirement_type is RequirementType.MANDATORY
        ),
        preferred_requirements=tuple(
            item.raw_text
            for item in requirements
            if item.requirement_type is RequirementType.PREFERRED
        ),
        benefits=_benefits(job.raw_description),
    )
