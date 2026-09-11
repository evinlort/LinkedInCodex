from pathlib import Path

from jobfit.config import load_taxonomy
from jobfit.matching import Taxonomy
from jobfit.profile import load_profile


def test_taxonomy_is_directional() -> None:
    profile = load_profile(Path("profiles/master_profile.yaml"))
    taxonomy = Taxonomy(load_taxonomy())
    inferred = taxonomy.infer("cicd", profile)
    assert inferred is not None and inferred[0].skill_id == "gitlab_ci"
    assert taxonomy.infer("gitlab_ci", profile) is None

