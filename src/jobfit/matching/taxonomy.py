from __future__ import annotations

from jobfit.models import CandidateProfile, ProfileSkill, TaxonomyEdge


class Taxonomy:
    def __init__(self, edges: tuple[TaxonomyEdge, ...]) -> None:
        self.edges = edges

    def infer(
        self, required_skill_id: str, profile: CandidateProfile
    ) -> tuple[ProfileSkill, TaxonomyEdge] | None:
        candidates: list[tuple[ProfileSkill, TaxonomyEdge]] = []
        for edge in self.edges:
            if not edge.scorable or edge.target != required_skill_id:
                continue
            profile_skill = profile.skills.get(edge.source)
            if profile_skill is not None:
                candidates.append((profile_skill, edge))
        if not candidates:
            return None
        return max(candidates, key=lambda item: item[1].score_factor)
