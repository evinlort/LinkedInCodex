from hashlib import sha256

from conftest import fixture_path

from jobfit.models import FetchedDocument
from jobfit.parsing.html import extract_job_posting


def _document(name: str) -> FetchedDocument:
    content = fixture_path(f"jobs/{name}").read_text(encoding="utf-8")
    return FetchedDocument(
        "linkedin", "4462925691", "https://www.linkedin.com/jobs/view/4462925691",
        content, "text/html", sha256(content.encode()).hexdigest()
    )


def test_json_ld_is_preferred() -> None:
    job = extract_job_posting(_document("linkedin_jsonld.html"))
    assert job.title == "Senior Python Engineer"
    assert job.company == "Example Labs"
    assert "Strong Python" in job.raw_description
    assert job.metadata["extraction_method"] == "json_ld"


def test_semantic_fallback() -> None:
    job = extract_job_posting(_document("linkedin_semantic.html"))
    assert job.title == "Backend Engineer"
    assert job.company == "Semantic Co"

