from __future__ import annotations

import hashlib
from pathlib import Path

from jobfit.errors import SourceError
from jobfit.models import FetchedDocument, JobLocator

MAX_LOCAL_BYTES = 5 * 1024 * 1024


class LocalFileJobSource:
    def __init__(self, path: Path, content_type: str) -> None:
        self.path = path
        self.content_type = content_type

    def fetch(self, locator: JobLocator) -> FetchedDocument:
        try:
            size = self.path.stat().st_size
            if size > MAX_LOCAL_BYTES:
                raise SourceError(f"Local job file exceeds {MAX_LOCAL_BYTES} bytes")
            content = self.path.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            raise SourceError("Local job file must be UTF-8") from exc
        except OSError as exc:
            raise SourceError(f"Cannot read local job file: {exc}") from exc
        if not content.strip():
            raise SourceError("Local job file is empty")
        return FetchedDocument(
            source="linkedin",
            source_id=locator.source_id,
            url=locator.url,
            content=content,
            content_type=self.content_type,
            content_hash=hashlib.sha256(content.encode("utf-8")).hexdigest(),
        )

