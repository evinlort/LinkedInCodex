from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from datetime import date
from pathlib import Path

from jobfit.errors import ConfigurationError, InputError, JobFitError, ParseError, SourceError
from jobfit.models import EvaluationRequest
from jobfit.pipeline import evaluate_job
from jobfit.reporting import render_json, render_text


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Deterministic LinkedIn job-fit evaluator")
    parser.add_argument("url", help="Public LinkedIn job URL")
    inputs = parser.add_mutually_exclusive_group()
    inputs.add_argument("--html", type=Path, help="Use a saved UTF-8 HTML page")
    inputs.add_argument("--text", type=Path, help="Use a saved UTF-8 job description")
    parser.add_argument("--profile", type=Path, default=Path("profiles/master_profile.yaml"))
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--as-of", type=date.fromisoformat, default=date.today())
    cache = parser.add_mutually_exclusive_group()
    cache.add_argument("--refresh", action="store_true")
    cache.add_argument("--no-cache", action="store_true")
    parser.add_argument("--cache-dir", type=Path, help=argparse.SUPPRESS)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    request = EvaluationRequest(
        url=args.url,
        profile_path=args.profile,
        html_path=args.html,
        text_path=args.text,
        as_of=args.as_of,
        refresh=args.refresh,
        no_cache=args.no_cache,
        cache_dir=args.cache_dir,
    )
    try:
        result = evaluate_job(request)
    except InputError as exc:
        print(f"Input error: {exc}", file=sys.stderr)
        return 2
    except SourceError as exc:
        print(f"Source error: {exc}", file=sys.stderr)
        return 3
    except ConfigurationError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 4
    except ParseError as exc:
        print(f"Parse error: {exc}", file=sys.stderr)
        return 5
    except JobFitError as exc:
        print(f"Job-fit error: {exc}", file=sys.stderr)
        return 5
    output = render_json(result) if args.format == "json" else render_text(result)
    if args.output:
        args.output.write_text(output + "\n", encoding="utf-8")
    else:
        print(output)
    return 0
