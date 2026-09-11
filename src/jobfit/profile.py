from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, cast

import yaml

from jobfit.errors import ConfigurationError
from jobfit.models import (
    AuthorizationHolding,
    CandidateProfile,
    LaborMarketAccess,
    LanguageProfile,
    LegalStatus,
    ProfileSkill,
    ResidenceAuthorization,
    SkillDepth,
    SkillState,
)


def _as_date(value: object, field: str) -> date:
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except ValueError as exc:
        raise ConfigurationError(f"{field} must be an ISO date") from exc


def _enum(enum_type: type[Any], value: object, field: str) -> Any:
    try:
        return enum_type(str(value))
    except ValueError as exc:
        raise ConfigurationError(f"Invalid {field}: {value}") from exc


def _load_skill(skill_id: str, raw: dict[str, Any]) -> ProfileSkill:
    state = cast(SkillState, _enum(SkillState, raw.get("state", "UNKNOWN"), "skill state"))
    depth_value = raw.get("depth")
    depth: SkillDepth | None = None
    if depth_value is not None:
        try:
            depth = SkillDepth[str(depth_value)]
        except KeyError as exc:
            raise ConfigurationError(f"Invalid depth for {skill_id}: {depth_value}") from exc
    if state is SkillState.NONE and depth is not SkillDepth.NONE:
        raise ConfigurationError(f"Skill {skill_id}: NONE state requires NONE depth")
    if state in {SkillState.VERIFIED, SkillState.LIMITED} and not raw.get("evidence"):
        raise ConfigurationError(f"Skill {skill_id}: verified state requires evidence")
    years = raw.get("verified_years")
    try:
        parsed_years = Decimal(str(years)) if years is not None else None
    except InvalidOperation as exc:
        raise ConfigurationError(f"Skill {skill_id}: invalid verified_years") from exc
    return ProfileSkill(
        skill_id=skill_id,
        state=state,
        depth=depth,
        evidence=tuple(str(item) for item in raw.get("evidence", [])),
        recency=str(raw["recency"]) if raw.get("recency") else None,
        experience_since=str(raw["experience_since"]) if raw.get("experience_since") else None,
        verified_years=parsed_years,
        boundary_note=str(raw["boundary_note"]) if raw.get("boundary_note") else None,
    )


def load_profile(path: Path) -> CandidateProfile:
    try:
        loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ConfigurationError(f"Cannot read profile {path}: {exc}") from exc
    except yaml.YAMLError as exc:
        raise ConfigurationError(f"Invalid profile YAML: {exc}") from exc
    if not isinstance(loaded, dict):
        raise ConfigurationError("Profile root must be a mapping")
    raw = cast(dict[str, Any], loaded)
    if int(raw.get("schema_version", 0)) != 1:
        raise ConfigurationError("Unsupported profile schema_version")

    ignored = tuple(str(item) for item in raw.get("ignored_entries", []))
    serialized = str(raw).casefold()
    for item in ignored:
        # The denylist itself is expected to contain the text; skill records are not.
        skills_text = str(raw.get("skills", {})).casefold()
        if item.casefold() in skills_text:
            raise ConfigurationError(f"Ignored profile entry leaked into skills: {item}")

    career = raw.get("career", {})
    location = raw.get("location", {})
    skills = {
        str(skill_id): _load_skill(str(skill_id), cast(dict[str, Any], value))
        for skill_id, value in raw.get("skills", {}).items()
    }
    languages = {
        str(name).casefold(): LanguageProfile(
            name=str(name).casefold(),
            stated_level=str(value["stated_level"]),
            cefr=str(value["cefr"]) if value.get("cefr") else None,
        )
        for name, value in raw.get("languages", {}).items()
    }
    legal_statuses: dict[str, LegalStatus] = {}
    for country, value in raw.get("legal_statuses", {}).items():
        country_code = str(country).upper()
        legal_statuses[country_code] = LegalStatus(
            country=country_code,
            labor_market_access=cast(
                LaborMarketAccess,
                _enum(LaborMarketAccess, value["labor_market_access"], "labor market access"),
            ),
            work_permit_required=(
                bool(value["work_permit_required"])
                if value.get("work_permit_required") is not None
                else None
            ),
            residence_authorization=cast(
                ResidenceAuthorization,
                _enum(
                    ResidenceAuthorization,
                    value["residence_authorization"],
                    "residence authorization",
                ),
            ),
            current_residence_authorization=cast(
                AuthorizationHolding,
                _enum(
                    AuthorizationHolding,
                    value.get("current_residence_authorization", "UNKNOWN"),
                    "current residence authorization",
                ),
            ),
            verified_on=_as_date(value["verified_on"], "verified_on"),
            review_due_month=(
                str(value["review_due_month"]) if value.get("review_due_month") else None
            ),
            evidence=tuple(str(item) for item in value.get("evidence", [])),
        )

    del serialized  # Kept out of validation errors because the profile may contain private data.
    return CandidateProfile(
        schema_version=1,
        profile_id=str(raw["profile_id"]),
        career_start=str(career["start"]),
        python_backend_start=(
            str(career["python_backend_start"]) if career.get("python_backend_start") else None
        ),
        current_country=(
            str(location["current_country"]) if location.get("current_country") else None
        ),
        current_city=str(location["current_city"]) if location.get("current_city") else None,
        relocation_targets=tuple(str(item) for item in location.get("relocation_targets", [])),
        citizenship=tuple(str(item) for item in raw.get("citizenship", [])),
        skills=skills,
        languages=languages,
        education=tuple(cast(dict[str, Any], item) for item in raw.get("education", [])),
        legal_statuses=legal_statuses,
        ignored_entries=ignored,
        source_metadata=cast(dict[str, Any], raw.get("source_metadata", {})),
    )


def completed_years(start: str, as_of: date) -> Decimal:
    """Conservative completed years for YYYY or YYYY-MM precision."""
    parts = start.split("-")
    if len(parts) == 1:
        return Decimal(max(0, as_of.year - int(parts[0]) - 1))
    year, month = int(parts[0]), int(parts[1])
    months = (as_of.year - year) * 12 + as_of.month - month
    if as_of.day < 1:  # Defensive; date always has day >= 1.
        months -= 1
    return Decimal(max(0, months)) / Decimal(12)
