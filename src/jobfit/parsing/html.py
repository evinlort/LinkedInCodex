from __future__ import annotations

import json
from collections.abc import Iterable
from typing import Any

from bs4 import BeautifulSoup

from jobfit.errors import ParseError
from jobfit.models import FetchedDocument, JobPosting


def _job_postings(value: Any) -> Iterable[dict[str, Any]]:
    if isinstance(value, list):
        for item in value:
            yield from _job_postings(item)
    elif isinstance(value, dict):
        kind = value.get("@type")
        kinds = kind if isinstance(kind, list) else [kind]
        if "JobPosting" in kinds:
            yield value
        if "@graph" in value:
            yield from _job_postings(value["@graph"])


def _plain_html(value: str) -> str:
    return BeautifulSoup(value, "html.parser").get_text("\n", strip=True)


def _location(value: Any) -> str | None:
    if isinstance(value, str):
        return value.strip() or None
    if isinstance(value, list):
        parts = [item for item in (_location(entry) for entry in value) if item]
        return "; ".join(parts) or None
    if isinstance(value, dict):
        address = value.get("address", value)
        if isinstance(address, dict):
            parts = [
                str(address[key]).strip()
                for key in ("addressLocality", "addressRegion", "addressCountry")
                if address.get(key)
            ]
            return ", ".join(parts) or None
    return None


def _meta(soup: BeautifulSoup, *keys: str) -> str | None:
    for key in keys:
        node = soup.find("meta", attrs={"property": key}) or soup.find(
            "meta", attrs={"name": key}
        )
        if node and node.get("content"):
            return str(node["content"]).strip() or None
    return None


def extract_job_posting(document: FetchedDocument) -> JobPosting:
    if document.content_type == "text/plain":
        return JobPosting(
            source=document.source,
            source_id=document.source_id,
            url=document.url,
            title=None,
            company=None,
            location=None,
            employment_type=None,
            work_model=None,
            raw_description=document.content.strip(),
            content_hash=document.content_hash,
            metadata={"extraction_method": "plain_text", "from_cache": document.from_cache},
        )

    soup = BeautifulSoup(document.content, "html.parser")
    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        try:
            payload = json.loads(script.string or script.get_text())
        except (json.JSONDecodeError, TypeError):
            continue
        posting = next(iter(_job_postings(payload)), None)
        if posting and posting.get("description"):
            organization = posting.get("hiringOrganization")
            company = organization.get("name") if isinstance(organization, dict) else None
            json_description = _plain_html(str(posting["description"]))
            if json_description:
                return JobPosting(
                    source=document.source,
                    source_id=document.source_id,
                    url=document.url,
                    title=str(posting["title"]).strip() if posting.get("title") else None,
                    company=str(company).strip() if company else None,
                    location=_location(posting.get("jobLocation")),
                    employment_type=(
                        str(posting["employmentType"]).strip()
                        if posting.get("employmentType")
                        else None
                    ),
                    work_model=None,
                    raw_description=json_description,
                    content_hash=document.content_hash,
                    metadata={
                        "extraction_method": "json_ld",
                        "from_cache": document.from_cache,
                        "retrieved_at": document.retrieved_at,
                    },
                )

    title_node = soup.find("h1")
    title: str | None = (
        title_node.get_text(" ", strip=True) if title_node else _meta(soup, "og:title")
    )
    company_node = soup.select_one("[itemprop='hiringOrganization'], .topcard__org-name-link")
    company = company_node.get_text(" ", strip=True) if company_node else None
    location_node = soup.select_one("[itemprop='jobLocation'], .topcard__flavor--bullet")
    location: str | None = location_node.get_text(" ", strip=True) if location_node else None
    description_node = soup.select_one(
        "[itemprop='description'], .show-more-less-html__markup, .description__text, main, article"
    )
    semantic_description = (
        description_node.get_text("\n", strip=True) if description_node else None
    )
    if not semantic_description:
        semantic_description = _meta(soup, "og:description", "description")
    if not semantic_description or not semantic_description.strip():
        raise ParseError("No public job description was found in the document")
    return JobPosting(
        source=document.source,
        source_id=document.source_id,
        url=document.url,
        title=title,
        company=company,
        location=location,
        employment_type=None,
        work_model=None,
        raw_description=semantic_description.strip(),
        content_hash=document.content_hash,
        metadata={
            "extraction_method": "semantic_html",
            "from_cache": document.from_cache,
            "retrieved_at": document.retrieved_at,
        },
    )
