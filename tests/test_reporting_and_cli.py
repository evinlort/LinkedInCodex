import json
from datetime import date
from pathlib import Path

from conftest import fixture_path

from jobfit.cli import main
from jobfit.models import EvaluationRequest
from jobfit.pipeline import evaluate_job
from jobfit.reporting import render_json, render_text


def test_reports_have_required_fields() -> None:
    result = evaluate_job(EvaluationRequest(
        "https://www.linkedin.com/jobs/view/4462925691",
        Path("profiles/master_profile.yaml"),
        text_path=fixture_path("jobs/english_backend.txt"), as_of=date(2026, 9, 11)
    ))
    payload = json.loads(render_json(result))
    assert payload["schema_version"] == "1.0"
    assert "requirements" in payload
    text = render_text(result)
    assert "Fit Score:" in text and "Hard blockers:" in text


def test_cli_json(capsys) -> None:
    code = main([
        "https://www.linkedin.com/jobs/view/4462925691", "--text",
        str(fixture_path("jobs/english_backend.txt")), "--format", "json",
        "--as-of", "2026-09-11",
    ])
    assert code == 0
    assert json.loads(capsys.readouterr().out)["job"]["source_id"] == "4462925691"

