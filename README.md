# LinkedIn Job Fit Engine

A local, deterministic Python application that compares a public LinkedIn job
description with a verified career profile. The runtime uses rules, exact phrase
matching and explicit evidence only—no LLM, embeddings, remote AI API, or
LinkedIn-profile skill scraping.

## Install and run

```bash
uv sync --extra dev
uv run python -m jobfit \
  "https://www.linkedin.com/jobs/view/4462925691"
```

LinkedIn may deny public access. Saved UTF-8 input is the reproducible fallback:

```bash
uv run python -m jobfit \
  "https://www.linkedin.com/jobs/view/4462925691" \
  --html job.html

uv run python -m jobfit \
  "https://www.linkedin.com/jobs/view/4462925691" \
  --text job.txt --format json --output result.json
```

Useful options are `--profile`, `--as-of`, `--refresh`, and `--no-cache`.
Successful evaluation returns exit code 0 even when the decision is
`DO_NOT_APPLY`. Input, source, profile/configuration and parse failures return
2, 3, 4 and 5 respectively.

## Evidence and determinism

`profiles/master_profile.yaml` is the source used at runtime. Missing skills are
`UNKNOWN`; only an explicit `NONE` is a verified gap. Fit is calculated from
determined evidence, while Confidence measures coverage and parser/matcher
quality. Hard blockers are evaluated separately from the numeric Fit.

For the same profile, rules, content hash and `--as-of` date, output is stable.
Live web content can change, so fetched pages are cached as immutable snapshots
under the operating system's user cache directory. Cache content is never
executed.

## Extending rules

- Add canonical skills and aliases to `src/jobfit/resources/skills.yaml`.
- Add only directed, explicit relations to `taxonomy.yaml`.
- Extend English/Czech headings and modalities in the other resource files.
- Add a sanitized regression fixture for every new ambiguity or parser rule.

Do not add LinkedIn profile imports or infer profile facts from a vacancy.

## Verification

```bash
uv run pytest
uv run ruff check .
uv run mypy src/jobfit
```

