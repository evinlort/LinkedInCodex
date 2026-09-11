from datetime import date
from pathlib import Path

from jobfit.models import LaborMarketAccess, SkillDepth, SkillState
from jobfit.profile import completed_years, load_profile


def test_master_profile_verified_facts() -> None:
    profile = load_profile(Path("profiles/master_profile.yaml"))
    assert profile.career_start == "2015-07"
    assert profile.python_backend_start == "2018-07"
    assert profile.skills["python"].depth is SkillDepth.STRONG
    assert profile.skills["kubernetes"].state is SkillState.NONE
    assert "sqlalchemy" not in profile.skills
    assert profile.legal_statuses["CZ"].labor_market_access is LaborMarketAccess.FREE_ACCESS
    assert profile.legal_statuses["CZ"].work_permit_required is False


def test_completed_years_is_conservative() -> None:
    assert completed_years("2015", date(2026, 9, 11)) == 10
    assert completed_years("2015-07", date(2026, 9, 11)) >= 11

