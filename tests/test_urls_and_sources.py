import httpx
import pytest
import respx

from jobfit.cache import JobCache
from jobfit.config import load_engine_config
from jobfit.errors import AccessRestrictedError, InputError, SourceError
from jobfit.sources import LinkedInPublicJobSource, parse_linkedin_url


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://www.linkedin.com/jobs/view/4462925691", "4462925691"),
        ("https://linkedin.com/jobs/view/senior-python-engineer-4462925691/", "4462925691"),
        ("https://www.linkedin.com/jobs/view/4462925691?trackingId=x", "4462925691"),
        ("4462925691", "4462925691"),
    ],
)
def test_linkedin_url(url: str, expected: str) -> None:
    assert parse_linkedin_url(url).source_id == expected


@pytest.mark.parametrize(
    "url",
    [
        "http://www.linkedin.com/jobs/view/123",
        "https://linkedin.com.example.org/jobs/view/123",
        "https://www.linkedin.com/in/person",
        "not a url",
    ],
)
def test_invalid_linkedin_url(url: str) -> None:
    with pytest.raises(InputError):
        parse_linkedin_url(url)


@respx.mock
def test_public_source_reads_html_without_credentials(tmp_path) -> None:
    locator = parse_linkedin_url("https://www.linkedin.com/jobs/view/4462925691")
    respx.get(locator.url).mock(
        return_value=httpx.Response(
            200,
            text="<main>Requirements: Python</main>",
            headers={"content-type": "text/html"},
        )
    )
    source = LinkedInPublicJobSource(
        load_engine_config(), JobCache(tmp_path), no_cache=True
    )
    assert "Python" in source.fetch(locator).content


@respx.mock
def test_public_source_rejects_external_redirect_before_following(tmp_path) -> None:
    locator = parse_linkedin_url("https://www.linkedin.com/jobs/view/4462925691")
    respx.get(locator.url).mock(
        return_value=httpx.Response(302, headers={"location": "https://example.org/secret"})
    )
    source = LinkedInPublicJobSource(
        load_engine_config(), JobCache(tmp_path), no_cache=True
    )
    with pytest.raises(SourceError, match="unsupported host"):
        source.fetch(locator)


@respx.mock
def test_public_source_detects_access_wall(tmp_path) -> None:
    locator = parse_linkedin_url("https://www.linkedin.com/jobs/view/4462925691")
    respx.get(locator.url).mock(
        return_value=httpx.Response(
            200,
            text="<div>Sign in to view this job</div>",
            headers={"content-type": "text/html"},
        )
    )
    guest_url = "https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/4462925691"
    respx.get(guest_url).mock(
        return_value=httpx.Response(
            200,
            text="<div class='authwall'>Join LinkedIn to view this job</div>",
            headers={"content-type": "text/html"},
        )
    )
    source = LinkedInPublicJobSource(
        load_engine_config(), JobCache(tmp_path), no_cache=True
    )
    with pytest.raises(AccessRestrictedError):
        source.fetch(locator)


@respx.mock
def test_public_source_uses_guest_page_after_access_wall(tmp_path) -> None:
    locator = parse_linkedin_url("4462925691")
    respx.get(locator.url).mock(
        return_value=httpx.Response(
            200,
            text="<div class='authwall'>Sign in to view this job</div>",
            headers={"content-type": "text/html"},
        )
    )
    guest_url = "https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/4462925691"
    respx.get(guest_url).mock(
        return_value=httpx.Response(
            200,
            text="<div class='show-more-less-html__markup'>Requirements: Python</div>",
            headers={"content-type": "text/html"},
        )
    )
    source = LinkedInPublicJobSource(
        load_engine_config(), JobCache(tmp_path), no_cache=True
    )
    assert "Requirements: Python" in source.fetch(locator).content
