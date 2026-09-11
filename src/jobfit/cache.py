from __future__ import annotations

import hashlib
import json
import os
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

from platformdirs import user_cache_path

from jobfit.models import FetchedDocument


class JobCache:
    def __init__(self, root: Path | None = None) -> None:
        self.root = root or user_cache_path("jobfit", ensure_exists=False)

    def get(self, source_id: str) -> FetchedDocument | None:
        index = self.root / "linkedin" / f"{source_id}.json"
        try:
            metadata = json.loads(index.read_text(encoding="utf-8"))
            content_path = index.parent / metadata["content_file"]
            content = content_path.read_text(encoding="utf-8")
        except (OSError, KeyError, json.JSONDecodeError):
            return None
        digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
        if digest != metadata.get("content_hash"):
            return None
        return FetchedDocument(
            source="linkedin",
            source_id=source_id,
            url=str(metadata["url"]),
            content=content,
            content_type=str(metadata.get("content_type", "text/html")),
            content_hash=digest,
            retrieved_at=metadata.get("retrieved_at"),
            from_cache=True,
        )

    def put(self, document: FetchedDocument) -> FetchedDocument:
        folder = self.root / "linkedin"
        folder.mkdir(parents=True, exist_ok=True, mode=0o700)
        content_name = f"{document.source_id}-{document.content_hash[:12]}.html"
        content_path = folder / content_name
        if not content_path.exists():
            content_path.write_text(document.content, encoding="utf-8")
            os.chmod(content_path, 0o600)
        retrieved_at = document.retrieved_at or datetime.now(UTC).isoformat()
        metadata = {
            "content_file": content_name,
            "content_hash": document.content_hash,
            "content_type": document.content_type,
            "retrieved_at": retrieved_at,
            "url": document.url,
        }
        temp_path = folder / f".{document.source_id}.json.tmp"
        index_path = folder / f"{document.source_id}.json"
        temp_path.write_text(json.dumps(metadata, sort_keys=True), encoding="utf-8")
        os.chmod(temp_path, 0o600)
        temp_path.replace(index_path)
        return replace(document, retrieved_at=retrieved_at)

