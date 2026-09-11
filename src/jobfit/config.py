from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from functools import lru_cache
from importlib.resources import files
from typing import Any, cast

import yaml

from jobfit.errors import ConfigurationError
from jobfit.models import ScoreComponent, SkillDefinition, TaxonomyEdge


@dataclass(frozen=True)
class EngineConfig:
    component_weights: dict[ScoreComponent, Decimal]
    decision_thresholds: dict[str, int]
    confidence_weights: dict[str, Decimal]
    matcher_quality: dict[str, Decimal]
    network: dict[str, int]


def _resource_yaml(name: str) -> dict[str, Any]:
    resource = files("jobfit.resources").joinpath(name)
    try:
        value = yaml.safe_load(resource.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise ConfigurationError(f"Cannot load resource {name}: {exc}") from exc
    if not isinstance(value, dict):
        raise ConfigurationError(f"Resource {name} must contain a mapping")
    return cast(dict[str, Any], value)


@lru_cache(maxsize=1)
def load_engine_config() -> EngineConfig:
    raw = _resource_yaml("engine.yaml")
    return EngineConfig(
        component_weights={
            ScoreComponent(key): Decimal(str(value))
            for key, value in raw["component_weights"].items()
        },
        decision_thresholds={key: int(value) for key, value in raw["decision_thresholds"].items()},
        confidence_weights={
            key: Decimal(str(value)) for key, value in raw["confidence_weights"].items()
        },
        matcher_quality={
            key: Decimal(str(value)) for key, value in raw["matcher_quality"].items()
        },
        network={key: int(value) for key, value in raw["network"].items()},
    )


@lru_cache(maxsize=1)
def load_sections() -> dict[str, list[str]]:
    raw = _resource_yaml("sections.yaml")
    return {key: [str(item) for item in value] for key, value in raw.items()}


@lru_cache(maxsize=1)
def load_requirement_rules() -> dict[str, Any]:
    return _resource_yaml("requirements.yaml")


@lru_cache(maxsize=1)
def load_skill_definitions() -> tuple[SkillDefinition, ...]:
    raw = _resource_yaml("skills.yaml")
    result: list[SkillDefinition] = []
    seen: set[str] = set()
    for item in raw.get("skills", []):
        skill_id = str(item["id"])
        if skill_id in seen:
            raise ConfigurationError(f"Duplicate skill id: {skill_id}")
        seen.add(skill_id)
        result.append(
            SkillDefinition(
                id=skill_id,
                canonical_name=str(item["name"]),
                aliases=tuple(str(alias) for alias in item["aliases"]),
                category=str(item.get("category", "technical")),
                fuzzy_enabled=bool(item.get("fuzzy_enabled", False)),
                ambiguous=bool(item.get("ambiguous", False)),
                positive_context=tuple(str(x).casefold() for x in item.get("positive_context", [])),
                negative_context=tuple(str(x).casefold() for x in item.get("negative_context", [])),
            )
        )
    return tuple(result)


@lru_cache(maxsize=1)
def load_taxonomy() -> tuple[TaxonomyEdge, ...]:
    raw = _resource_yaml("taxonomy.yaml")
    return tuple(
        TaxonomyEdge(
            source=str(item["source"]),
            target=str(item["target"]),
            relation=str(item["relation"]),
            score_factor=Decimal(str(item["score_factor"])),
            scorable=bool(item["scorable"]),
        )
        for item in raw.get("edges", [])
    )
