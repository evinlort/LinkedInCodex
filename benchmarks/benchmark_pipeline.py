"""Informational deterministic-core benchmark; network time is excluded."""

from __future__ import annotations

import argparse
import time
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory

from jobfit.models import EvaluationRequest
from jobfit.pipeline import evaluate_job


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--jobs", type=int, default=1000)
    args = parser.parse_args()
    text = """Requirements:
- Strong Python experience
- PostgreSQL and RabbitMQ
Responsibilities:
- Build microservices and REST APIs
Nice to Have:
- Docker
"""
    with TemporaryDirectory() as folder:
        path = Path(folder) / "job.txt"
        path.write_text(text, encoding="utf-8")
        request = EvaluationRequest(
            url="https://www.linkedin.com/jobs/view/4462925691",
            profile_path=Path("profiles/master_profile.yaml"),
            text_path=path,
            as_of=date(2026, 9, 11),
        )
        evaluate_job(request)  # warm-up and matcher compilation cost observation
        started = time.perf_counter()
        for _ in range(args.jobs):
            evaluate_job(request)
        elapsed = time.perf_counter() - started
    print(f"jobs={args.jobs} seconds={elapsed:.3f} ms_per_job={elapsed / args.jobs * 1000:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

