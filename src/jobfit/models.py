from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from enum import IntEnum, StrEnum
from pathlib import Path
from typing import Any


class RequirementType(StrEnum):
    MANDATORY = "MANDATORY"
    CORE_RESPONSIBILITY = "CORE_RESPONSIBILITY"
    PREFERRED = "PREFERRED"
    CONTEXT = "CONTEXT"


class ExpressionOp(StrEnum):
    ATOM = "ATOM"
    ANY = "ANY"
    ALL = "ALL"
    COMPOSITE = "COMPOSITE"
    REVIEW = "REVIEW"


class SkillState(StrEnum):
    VERIFIED = "VERIFIED"
    LIMITED = "LIMITED"
    NONE = "NONE"
    UNKNOWN = "UNKNOWN"


class SkillDepth(IntEnum):
    NONE = 0
    EXPOSURE = 1
    WORKING = 2
    STRONG = 3
    EXPERT = 4


class ScoreComponent(StrEnum):
    MANDATORY_ROLE = "mandatory_role"
    CORE_RESPONSIBILITIES = "core_responsibilities"
    SENIORITY = "seniority"
    DOMAIN = "domain"
    COMPATIBILITY = "compatibility"
    PREFERRED = "preferred"


class MatchStatus(StrEnum):
    STRONG = "STRONG"
    PARTIAL = "PARTIAL"
    VERIFIED_GAP = "VERIFIED_GAP"
    UNKNOWN = "UNKNOWN"
    OPTIONAL_GAP = "OPTIONAL_GAP"
    REVIEW = "REVIEW"


class MatchingMethod(StrEnum):
    EXACT = "EXACT"
    CONTEXT_EXACT = "CONTEXT_EXACT"
    TAXONOMY = "TAXONOMY"
    FUZZY = "FUZZY"
    RULE = "RULE"


class Decision(StrEnum):
    EXCELLENT_FIT = "EXCELLENT_FIT"
    GOOD_FIT = "GOOD_FIT"
    BORDERLINE = "BORDERLINE"
    WEAK_FIT = "WEAK_FIT"
    DO_NOT_APPLY = "DO_NOT_APPLY"
    MANUAL_REVIEW = "MANUAL_REVIEW"


class LaborMarketAccess(StrEnum):
    FREE_ACCESS = "FREE_ACCESS"
    RESTRICTED = "RESTRICTED"
    UNKNOWN = "UNKNOWN"


class ResidenceAuthorization(StrEnum):
    REQUIRED = "REQUIRED"
    NOT_REQUIRED = "NOT_REQUIRED"
    UNKNOWN = "UNKNOWN"


class AuthorizationHolding(StrEnum):
    HELD = "HELD"
    NOT_HELD = "NOT_HELD"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class SourceSpan:
    start: int
    end: int
    text: str


@dataclass(frozen=True)
class SkillDefinition:
    id: str
    canonical_name: str
    aliases: tuple[str, ...]
    category: str = "technical"
    fuzzy_enabled: bool = False
    ambiguous: bool = False
    positive_context: tuple[str, ...] = ()
    negative_context: tuple[str, ...] = ()


@dataclass(frozen=True)
class ProfileSkill:
    skill_id: str
    state: SkillState
    depth: SkillDepth | None
    evidence: tuple[str, ...]
    recency: str | None = None
    experience_since: str | None = None
    verified_years: Decimal | None = None
    boundary_note: str | None = None


@dataclass(frozen=True)
class LanguageProfile:
    name: str
    stated_level: str
    cefr: str | None = None


@dataclass(frozen=True)
class LegalStatus:
    country: str
    labor_market_access: LaborMarketAccess
    work_permit_required: bool | None
    residence_authorization: ResidenceAuthorization
    current_residence_authorization: AuthorizationHolding
    verified_on: date
    review_due_month: str | None = None
    evidence: tuple[str, ...] = ()


@dataclass(frozen=True)
class CandidateProfile:
    schema_version: int
    profile_id: str
    career_start: str
    python_backend_start: str | None
    current_country: str | None
    current_city: str | None
    relocation_targets: tuple[str, ...]
    citizenship: tuple[str, ...]
    skills: dict[str, ProfileSkill]
    languages: dict[str, LanguageProfile]
    education: tuple[dict[str, Any], ...]
    legal_statuses: dict[str, LegalStatus]
    ignored_entries: tuple[str, ...]
    source_metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class TaxonomyEdge:
    source: str
    target: str
    relation: str
    score_factor: Decimal
    scorable: bool


@dataclass(frozen=True)
class JobLocator:
    url: str
    source_id: str


@dataclass(frozen=True)
class FetchedDocument:
    source: str
    source_id: str
    url: str
    content: str
    content_type: str
    content_hash: str
    retrieved_at: str | None = None
    from_cache: bool = False


@dataclass(frozen=True)
class JobPosting:
    source: str
    source_id: str
    url: str
    title: str | None
    company: str | None
    location: str | None
    employment_type: str | None
    work_model: str | None
    raw_description: str
    content_hash: str
    metadata: dict[str, Any] = field(default_factory=dict)
    responsibilities: tuple[str, ...] = ()
    mandatory_requirements: tuple[str, ...] = ()
    preferred_requirements: tuple[str, ...] = ()
    benefits: tuple[str, ...] = ()
    salary: str | None = None


@dataclass(frozen=True)
class SkillMention:
    skill_id: str
    canonical_name: str
    span: SourceSpan
    method: MatchingMethod
    matcher_quality: Decimal


@dataclass(frozen=True)
class Requirement:
    id: str
    raw_text: str
    span: SourceSpan
    section: str | None
    requirement_type: RequirementType
    component: ScoreComponent
    expression_op: ExpressionOp
    required_depth: SkillDepth | None
    minimum_years: Decimal | None
    years_subject: str | None
    parser_confidence: Decimal
    mentions: tuple[SkillMention, ...] = ()
    review_reason: str | None = None


@dataclass(frozen=True)
class MatchEvidence:
    skill_id: str | None
    canonical_skill: str | None
    matched_job_text: str
    candidate_level: int | None
    required_level: int | None
    requirement_type: RequirementType
    matching_method: MatchingMethod
    score: Decimal | None
    source_span: SourceSpan
    profile_evidence: tuple[str, ...] = ()
    taxonomy_inference: str | None = None


@dataclass(frozen=True)
class RequirementResult:
    requirement: Requirement
    status: MatchStatus
    score: Decimal | None
    evidence: tuple[MatchEvidence, ...]
    blocker: bool = False
    reason: str | None = None
    score_contribution: Decimal | None = None


@dataclass(frozen=True)
class ComponentResult:
    component: ScoreComponent
    maximum_weight: Decimal
    ratio: Decimal | None
    awarded_points: Decimal | None
    determined_count: int
    unknown_count: int


@dataclass(frozen=True)
class FitResult:
    schema_version: str
    job: JobPosting
    evaluated_as_of: date
    fit_score: int | None
    confidence_score: int
    decision: Decision
    requirements: tuple[RequirementResult, ...]
    components: tuple[ComponentResult, ...]
    blockers: tuple[str, ...]
    legal_notes: tuple[str, ...]
    diagnostics: tuple[str, ...]


@dataclass(frozen=True)
class EvaluationRequest:
    url: str
    profile_path: Path
    html_path: Path | None = None
    text_path: Path | None = None
    as_of: date = field(default_factory=date.today)
    refresh: bool = False
    no_cache: bool = False
    cache_dir: Path | None = None
