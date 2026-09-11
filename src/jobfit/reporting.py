from __future__ import annotations

import json
from dataclasses import fields, is_dataclass
from datetime import date
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Any, cast

from jobfit.models import FitResult, MatchStatus, RequirementResult


def _primitive(value: Any) -> Any:
    if is_dataclass(value):
        return {field.name: _primitive(getattr(value, field.name)) for field in fields(value)}
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _primitive(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_primitive(item) for item in value]
    return value


def result_to_dict(result: FitResult) -> dict[str, Any]:
    return cast(dict[str, Any], _primitive(result))


def render_json(result: FitResult) -> str:
    return json.dumps(result_to_dict(result), ensure_ascii=False, indent=2, sort_keys=True)


def _label(item: RequirementResult) -> str:
    skills = ", ".join(
        evidence.canonical_skill for evidence in item.evidence if evidence.canonical_skill
    )
    return skills or item.requirement.raw_text


def _section(title: str, items: list[RequirementResult]) -> list[str]:
    lines = [f"{title}:"]
    if not items:
        lines.append("  None")
    else:
        for item in items:
            suffix = f" — {item.reason}" if item.reason else ""
            lines.append(f"  - {_label(item)}{suffix}")
    return lines


def render_text(result: FitResult) -> str:
    job = result.job
    lines = [
        f"Company: {job.company or 'Unknown'}",
        f"Position: {job.title or 'Unknown'}",
        f"Location: {job.location or 'Unknown'}",
        f"LinkedIn Job ID: {job.source_id}",
        f"Fit Score: {result.fit_score if result.fit_score is not None else 'N/A'}/100",
        f"Confidence Score: {result.confidence_score}%",
        f"Decision: {result.decision.value}",
        "",
    ]
    groups = {
        "Strong matches": [
            item for item in result.requirements if item.status is MatchStatus.STRONG
        ],
        "Partial matches": [
            item for item in result.requirements if item.status is MatchStatus.PARTIAL
        ],
        "Verified missing skills": [
            item for item in result.requirements if item.status is MatchStatus.VERIFIED_GAP
        ],
        "Unknown/unverified requirements": [
            item
            for item in result.requirements
            if item.status in {MatchStatus.UNKNOWN, MatchStatus.REVIEW}
        ],
        "Optional gaps": [
            item for item in result.requirements if item.status is MatchStatus.OPTIONAL_GAP
        ],
    }
    for title, items in groups.items():
        lines.extend(_section(title, items))
        lines.append("")
    lines.append("Hard blockers:")
    lines.extend([f"  - {item}" for item in result.blockers] or ["  None"])
    lines.append("")
    lines.append("Legal/location notes:")
    lines.extend([f"  - {item}" for item in result.legal_notes] or ["  None"])
    lines.append("")
    recommendation = {
        "EXCELLENT_FIT": "Apply; emphasize the strongest verified evidence.",
        "GOOD_FIT": "Apply with a targeted CV and address partial gaps.",
        "BORDERLINE": "Review gaps before deciding whether to apply.",
        "WEAK_FIT": "Apply only if the role is strategically valuable.",
        "DO_NOT_APPLY": "Do not apply unless the blocker or evidence changes.",
        "MANUAL_REVIEW": "Resolve unknown or ambiguous requirements before deciding.",
    }[result.decision.value]
    lines.append(f"Recommendation: {recommendation}")
    return "\n".join(lines)
