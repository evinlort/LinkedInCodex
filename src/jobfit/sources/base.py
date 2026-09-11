from __future__ import annotations

import re
from typing import Protocol
from urllib.parse import urlsplit

from jobfit.errors import InputError
from jobfit.models import FetchedDocument, JobLocator

LINKEDIN_HOSTS = {"linkedin.com", "www.linkedin.com"}
JOB_PATH_RE = re.compile(r"^/jobs/view/(?:[^/?#]*-)?([1-9][0-9]{0,19})/?$")
JOB_ID_RE = re.compile(r"^[1-9][0-9]{0,19}$")


class JobSource(Protocol):
    def fetch(self, locator: JobLocator) -> FetchedDocument: ...


def parse_linkedin_url(url: str) -> JobLocator:
    value = url.strip()
    if JOB_ID_RE.fullmatch(value):
        return JobLocator(
            url=f"https://www.linkedin.com/jobs/view/{value}",
            source_id=value,
        )
    parsed = urlsplit(value)
    if parsed.scheme != "https":
        raise InputError("LinkedIn URL must use https")
    if parsed.username or parsed.password:
        raise InputError("Credentials are not allowed in a LinkedIn URL")
    host = (parsed.hostname or "").lower().rstrip(".")
    if host not in LINKEDIN_HOSTS:
        raise InputError("URL host must be linkedin.com or www.linkedin.com")
    match = JOB_PATH_RE.fullmatch(parsed.path)
    if not match:
        raise InputError("Expected a LinkedIn /jobs/view/<numeric-id> URL or a numeric job ID")
    source_id = match.group(1)
    return JobLocator(
        url=f"https://www.linkedin.com/jobs/view/{source_id}",
        source_id=source_id,
    )
