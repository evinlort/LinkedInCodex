from __future__ import annotations

import hashlib
from urllib.parse import urljoin, urlsplit

import httpx
from bs4 import BeautifulSoup

from jobfit.cache import JobCache
from jobfit.config import EngineConfig
from jobfit.errors import AccessRestrictedError, SourceError
from jobfit.models import FetchedDocument, JobLocator


class LinkedInPublicJobSource:
    def __init__(
        self,
        config: EngineConfig,
        cache: JobCache,
        *,
        refresh: bool = False,
        no_cache: bool = False,
    ) -> None:
        self.config = config
        self.cache = cache
        self.refresh = refresh
        self.no_cache = no_cache

    def fetch(self, locator: JobLocator) -> FetchedDocument:
        if not self.refresh and not self.no_cache:
            cached = self.cache.get(locator.source_id)
            if cached is not None:
                return cached

        try:
            content = self._download(locator.url)
            if self._looks_restricted(content):
                raise AccessRestrictedError("LinkedIn returned an authentication wall")
        except AccessRestrictedError:
            guest_url = (
                "https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/"
                f"{locator.source_id}"
            )
            content = self._download(guest_url)
            if self._looks_restricted(content):
                raise AccessRestrictedError(
                    "LinkedIn public and guest pages both require authentication"
                ) from None

        document = FetchedDocument(
            source="linkedin",
            source_id=locator.source_id,
            url=locator.url,
            content=content,
            content_type="text/html",
            content_hash=hashlib.sha256(content.encode("utf-8")).hexdigest(),
        )
        return document if self.no_cache else self.cache.put(document)

    def _download(self, url: str) -> str:
        timeout = httpx.Timeout(
            connect=self.config.network["connect_timeout_seconds"],
            read=self.config.network["read_timeout_seconds"],
            write=self.config.network["read_timeout_seconds"],
            pool=self.config.network["connect_timeout_seconds"],
        )
        try:
            with httpx.Client(
                timeout=timeout,
                follow_redirects=False,
                headers={"User-Agent": "jobfit/0.1 (+deterministic public-job reader)"},
            ) as client:
                current_url = url
                chunks: list[bytes] | None = None
                for redirect_count in range(self.config.network["max_redirects"] + 1):
                    with client.stream("GET", current_url) as response:
                        if response.status_code in {301, 302, 303, 307, 308}:
                            location = response.headers.get("location")
                            if not location:
                                raise SourceError("LinkedIn returned a redirect without Location")
                            if redirect_count >= self.config.network["max_redirects"]:
                                raise SourceError("LinkedIn exceeded the redirect limit")
                            redirected = urljoin(current_url, location)
                            parsed = urlsplit(redirected)
                            if parsed.scheme != "https" or (parsed.hostname or "").lower() not in {
                                "linkedin.com",
                                "www.linkedin.com",
                            }:
                                raise SourceError("LinkedIn redirected to an unsupported host")
                            current_url = redirected
                            continue
                        if response.status_code in {401, 403, 429}:
                            raise AccessRestrictedError(
                                f"LinkedIn public access returned HTTP {response.status_code}"
                            )
                        response.raise_for_status()
                        content_type = response.headers.get("content-type", "").lower()
                        if "html" not in content_type:
                            raise SourceError(
                                f"Expected HTML, got {content_type or 'unknown content'}"
                            )
                        chunks = []
                        total = 0
                        for chunk in response.iter_bytes():
                            total += len(chunk)
                            if total > self.config.network["max_bytes"]:
                                raise SourceError(
                                    "LinkedIn response exceeds the configured size limit"
                                )
                            chunks.append(chunk)
                        break
                if chunks is None:
                    raise SourceError("LinkedIn did not return a final HTML response")
        except AccessRestrictedError:
            raise
        except httpx.HTTPError as exc:
            raise SourceError(f"Cannot retrieve public LinkedIn job: {exc}") from exc

        return b"".join(chunks).decode("utf-8", errors="replace")

    @staticmethod
    def _looks_restricted(content: str) -> bool:
        soup = BeautifulSoup(content, "html.parser")
        if soup.select_one(
            "[itemprop='description'], .show-more-less-html__markup, .description__text"
        ):
            return False
        for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
            if "JobPosting" in (script.string or script.get_text()):
                return False
        if soup.select_one(".authwall, #captcha-challenge, iframe[src*='captcha']"):
            return True
        folded = soup.get_text(" ", strip=True).casefold()
        return any(
            marker in folded
            for marker in (
                "sign in to view this job",
                "join linkedin to view this job",
                "security verification",
            )
        )
