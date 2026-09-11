from __future__ import annotations

from functools import lru_cache

from jobfit.cache import JobCache
from jobfit.config import (
    load_engine_config,
    load_skill_definitions,
    load_taxonomy,
)
from jobfit.evaluation import evaluate_requirements
from jobfit.matching import SkillMatcher, Taxonomy
from jobfit.models import EvaluationRequest, FitResult
from jobfit.parsing import extract_job_posting, parse_requirements, structure_job
from jobfit.profile import load_profile
from jobfit.scoring import score_fit
from jobfit.sources import (
    JobSource,
    LinkedInPublicJobSource,
    LocalFileJobSource,
    parse_linkedin_url,
)


@lru_cache(maxsize=1)
def _compiled_matcher() -> SkillMatcher:
    return SkillMatcher(load_skill_definitions())


@lru_cache(maxsize=1)
def _compiled_taxonomy() -> Taxonomy:
    return Taxonomy(load_taxonomy())


def evaluate_job(request: EvaluationRequest) -> FitResult:
    config = load_engine_config()
    profile = load_profile(request.profile_path)
    locator = parse_linkedin_url(request.url)
    source: JobSource
    if request.html_path is not None:
        source = LocalFileJobSource(request.html_path, "text/html")
    elif request.text_path is not None:
        source = LocalFileJobSource(request.text_path, "text/plain")
    else:
        source = LinkedInPublicJobSource(
            config,
            JobCache(request.cache_dir),
            refresh=request.refresh,
            no_cache=request.no_cache,
        )
    document = source.fetch(locator)
    job = extract_job_posting(document)
    requirements, section_quality = parse_requirements(job)
    job = structure_job(job, requirements)
    matcher = _compiled_matcher()
    attached = tuple(matcher.attach(requirement) for requirement in requirements)
    evaluated, legal_notes = evaluate_requirements(
        attached, profile, _compiled_taxonomy(), request.as_of
    )
    diagnostics: list[str] = []
    if not requirements:
        diagnostics.append("No deterministically scorable requirement lines were found")
    return score_fit(
        job,
        evaluated,
        config,
        request.as_of,
        section_quality,
        legal_notes,
        tuple(diagnostics),
    )
