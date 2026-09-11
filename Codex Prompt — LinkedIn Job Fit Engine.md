You are a Senior Python Software Architect and Senior Python Developer.

Your task is to PLAN first, and only after my explicit approval IMPLEMENT, a deterministic Python application that evaluates how well my verified professional profile matches a LinkedIn job vacancy.

IMPORTANT WORKFLOW RULE:

PHASE 1 — PLAN ONLY.

On the first run:
- inspect the repository;
- inspect the existing Master Skills / Career Profile files;
- inspect existing Python project structure, configuration, tests and dependencies;
- do NOT modify any files;
- do NOT write implementation code;
- do NOT install packages;
- do NOT refactor anything;
- return a detailed implementation plan IN RUSSIAN for my review;
- explicitly list assumptions, risks, proposed files/modules, data structures, algorithms, tests and implementation stages;
- then STOP.

Do not start PHASE 2 until I explicitly approve the plan.

PHASE 2 — IMPLEMENTATION.

After approval:
- implement only the approved scope;
- use small, reviewable changes;
- do not refactor unrelated code;
- do not add unnecessary abstractions;
- do not invent profile information;
- add tests together with implementation;
- verify the result after each meaningful stage.

==================================================
1. PROJECT GOAL
==================================================

Build a local Python "LinkedIn Job Fit Engine".

Primary usage should eventually look similar to:

    python -m jobfit \
        "https://www.linkedin.com/jobs/view/4462925691"

or an equivalent CLI appropriate for the existing repository.

The application must:

1. Accept a LinkedIn job URL.
2. Extract the LinkedIn job ID.
3. Retrieve the publicly available job posting when possible.
4. Parse the job description into structured requirements.
5. Extract technical skills and other relevant conditions.
6. Compare them against my verified Master Skills file.
7. Detect:
   - strong matches;
   - partial matches;
   - verified gaps;
   - unknown/unverified skills;
   - optional gaps;
   - hard blockers.
8. Calculate an explainable Fit Score.
9. Calculate a separate Confidence Score.
10. Produce a human-readable report.
11. Produce structured machine-readable output, preferably JSON.
12. Preserve evidence explaining every important decision.

The runtime solution MUST be 100% deterministic.

Do NOT use:
- LLMs;
- OpenAI APIs;
- Gemini;
- Claude;
- external AI APIs;
- vector embeddings;
- semantic embedding models;
- AI-based classification;
- generative AI;
- remote AI services.

Using Codex to BUILD the software is allowed.
The resulting software itself must contain no AI dependency.

==================================================
2. VERIFIED PROFILE FACTS
==================================================

The existing Master Skills / Career Profile is the source of truth.

DO NOT replace it with information scraped from LinkedIn.

DO NOT infer new skills from job descriptions.

DO NOT silently upgrade a skill level.

Important verified correction:

I have worked professionally as a programmer/software developer since 2015.

Prefer storing the source fact:

    career_start_year: 2015

rather than hard-coding:

    years_experience: 11

If an exact career-start month/date exists in the Master file, use it.

If only the year 2015 is known, do NOT invent an exact month. For requirements where the distinction matters, use a conservative deterministic calculation or represent the experience as "since 2015".

For normal requirements such as:

    3+ years
    5+ years

the profile clearly satisfies them.

Do not independently infer years of experience with an individual technology unless that information exists in the Master profile.

==================================================
3. OBSOLETE LINKEDIN PROFILE ENTRY
==================================================

The LinkedIn profile entry:

    Infinidash and python :) (Professional Working)

will be removed from LinkedIn.

It MUST NOT be considered a valid skill, qualification or evidence.

The application must not depend on LinkedIn-profile skill extraction.

The Master Skills file, not LinkedIn profile data, is authoritative.

If this obsolete string appears in imported/cached profile data, it should be ignored.

Do not infer any skill from this string.

==================================================
4. CZECH LABOUR-MARKET STATUS
==================================================

This is a VERIFIED legal/profile fact and must be modelled correctly.

Citizenship:

    Israel

Czech labour-market status:

    labor_market_access = FREE_ACCESS
    work_permit_required = false

Israeli citizens have free access to the Czech labour market.

They do not require a Czech employment permit / work permit / dual Employee Card / Blue Card merely to obtain access to employment.

However:

    residence_authorization = REQUIRED

Free labour-market access does NOT itself provide a right of residence in the Czech Republic.

These concepts MUST be kept separate.

Do NOT model this as simply:

    visa_required = false

Do NOT model it as simply:

    sponsorship_required = false

because those formulations can be misleading.

Design explicit enums/data fields for concepts such as:

    LaborMarketAccess.FREE_ACCESS
    ResidenceAuthorization.REQUIRED

and possibly other states if useful.

When evaluating Czech vacancies:

A requirement equivalent to:

    "candidate must be eligible to work in Czechia"

must NOT automatically fail merely because the candidate is an Israeli citizen.

A requirement equivalent to:

    "we cannot obtain/provide a residence permit"
    "must already hold Czech residence authorization"
    "must currently reside in Czech Republic"

is a separate condition and must be evaluated separately if the Master profile contains enough information.

If wording such as:

    "no visa sponsorship"
    "no sponsorship available"

is ambiguous between work authorization and residence status, do NOT guess.

Classify it as requiring review / UNKNOWN unless deterministic rules can establish its meaning from context.

The design must preserve this distinction.

==================================================
5. LINKEDIN INPUT
==================================================

Support at least standard LinkedIn job URLs such as:

    https://www.linkedin.com/jobs/view/4462925691

and URLs containing a slug before the numeric ID.

The LinkedIn job ID should be extracted deterministically.

Design LinkedIn access behind an adapter/interface, for example conceptually:

    JobSource
        LinkedInPublicJobSource

Do not tightly couple the scoring engine to LinkedIn HTML.

The architecture should allow adding other job sources later.

Prefer extraction order similar to:

1. structured JSON-LD JobPosting when available;
2. stable public HTML fields;
3. generic structured/semantic fallback;
4. explicit failure.

Do NOT bypass:
- authentication;
- CAPTCHA;
- LinkedIn access controls;
- anti-bot restrictions.

If LinkedIn does not expose the vacancy publicly, fail cleanly and support a deterministic fallback such as:

    --html job.html

or:

    --text job.txt

so the matching/scoring engine can still be used without LinkedIn retrieval.

Consider local caching by LinkedIn job ID to:
- avoid repeatedly fetching the same vacancy;
- simplify testing;
- reduce external requests.

Do not store credentials.

==================================================
6. STRUCTURED JOB MODEL
==================================================

Do not treat the entire vacancy as one unstructured string after retrieval.

Propose a data model similar to:

    JobPosting
        source
        source_id
        url
        title
        company
        location
        employment_type
        work_model
        raw_description
        responsibilities[]
        mandatory_requirements[]
        preferred_requirements[]
        benefits[]
        salary
        metadata

The exact model should follow the repository conventions.

Requirements should become explicit objects.

For example conceptually:

    Requirement
        raw_text
        section
        requirement_type
        importance
        canonical_skills[]
        required_level
        minimum_years
        matching_mode
        evidence

==================================================
7. REQUIREMENT TYPES
==================================================

At minimum distinguish:

    MANDATORY
    CORE_RESPONSIBILITY
    PREFERRED
    CONTEXT

Do NOT infer importance only from words such as:

    experience
    knowledge
    strong

Section context must have priority.

For example:

    Nice to have:
    Experience with C++

must remain PREFERRED, not MANDATORY.

The parser should recognize common English LinkedIn sections such as:

    Requirements
    Qualifications
    Must Have
    What You Need
    Responsibilities
    What You'll Do
    Nice to Have
    Preferred
    Bonus

Because the target job market is Czech Republic, propose deterministic support for common Czech equivalents as well, for example:

    Požadavky
    Kvalifikace
    Náplň práce
    Co budete dělat
    Výhodou
    Výhodou je
    Požadujeme

Do not use AI language classification.

Rule tables/configuration files are preferred.

==================================================
8. TEXT NORMALIZATION
==================================================

Technical syntax MUST be preserved.

Do not strip punctuation blindly.

These must remain distinguishable:

    C
    C++
    C#
    F#
    .NET
    ASP.NET
    Node.js
    CI/CD
    Objective-C
    Power BI
    Git
    GitLab
    Go

Use separate representations:

A. surface representation
   - exact/phrase matching;
   - preserves technical punctuation.

B. linguistic/rule representation
   - normalization;
   - optional deterministic lemmatization;
   - section/context rules.

Use Unicode normalization and whitespace normalization carefully.

Do not destroy source offsets if match evidence must refer to the original vacancy.

==================================================
9. SKILL MATCHING
==================================================

For approximately 1,000+ Master skills/aliases, the initial architecture should prefer a deterministic exact/phrase layer.

Consider:

    spaCy blank pipeline
    spaCy PhraseMatcher(attr="LOWER")

Do not load statistical/AI spaCy models.

Use:

    spacy.blank(...)

where appropriate.

The same tokenizer must be used to compile skill aliases and process vacancies.

Aho-Corasick may be considered later if benchmarks justify it.

Do NOT add Aho-Corasick merely because it is theoretically faster.

For the expected initial scale, prioritize correctness, maintainability and evidence spans.

RapidFuzz may be used only as a restricted fallback.

==================================================
10. MASTER SKILLS DATA MODEL
==================================================

Inspect the existing Master Skills file before proposing changes.

Do not replace it unnecessarily.

If normalization is required, propose the smallest migration possible.

Each canonical skill should conceptually be able to represent:

    id
    canonical_name
    aliases
    category
    state
    level
    years
    last_used / recency if available
    evidence
    boundaries
    fuzzy_enabled
    ambiguity_policy

Use stable canonical IDs internally.

Example:

    python
    postgresql
    gitlab_ci
    docker
    kubernetes
    cpp
    aws

Do not use presentation strings as primary keys.

==================================================
11. SKILL STATES
==================================================

The engine MUST distinguish UNKNOWN from NONE.

Suggested states:

    VERIFIED
    LIMITED
    NONE
    UNKNOWN

Examples:

A skill explicitly documented as absent:

    C++ = NONE

means:

    verified gap

A skill that simply does not occur in the Master profile:

    SQLAlchemy = UNKNOWN

means:

    insufficient information

It MUST NOT automatically mean:

    candidate does not know SQLAlchemy

This distinction is critical for Confidence Score.

==================================================
12. SKILL DEPTH
==================================================

Propose a simple deterministic skill-depth scale such as:

    0 = NONE
    1 = EXPOSURE
    2 = WORKING
    3 = STRONG
    4 = EXPERT

Do not silently change existing Master terminology without presenting the mapping in the plan.

A job requirement should also receive a required depth.

Example deterministic vocabulary:

    familiarity / basic / exposure          -> 1
    experience / hands-on / practical       -> 2
    strong / solid / proficient / advanced  -> 3
    deep expertise / expert / extensive     -> 4

Create English and, where practical, Czech rule tables.

These levels must be configurable/testable rather than scattered as magic constants.

==================================================
13. SKILL DEPTH MATCH
==================================================

A candidate mentioning a skill is not automatically a full match.

Example:

Job:

    Solid Docker skills

Master:

    Docker = LIMITED / EXPOSURE

This must produce a PARTIAL match, not a full match.

A possible base formula is:

    min(candidate_level / required_level, 1.0)

but critically evaluate it in the plan and propose adjustments if necessary.

The final formula must remain deterministic and explainable.

==================================================
14. BOOLEAN / COMPOSITE REQUIREMENTS
==================================================

Support requirement structures such as:

    ANY
    ALL
    COMPOSITE

Example:

    Flask/FastAPI

may mean:

    ANY(flask, fastapi)

where either accepted framework satisfies the requirement.

But:

    PostgreSQL, SQLite and ORM frameworks such as SQLAlchemy

must NOT be collapsed into one keyword.

It may represent separate capabilities:

    relational database experience
    specific database technology
    ORM experience

The plan must describe how conjunctions, alternatives and examples will be represented without pretending to understand arbitrary natural language.

Prefer conservative rules.

When uncertain:

    UNKNOWN / REVIEW

is better than a fabricated interpretation.

==================================================
15. TAXONOMY AND SYNONYMS
==================================================

Canonical alias mapping should be deterministic.

Examples:

    AWS
    Amazon Web Services

may map to:

    aws

But:

    Amazon EC2

is NOT simply a synonym for AWS.

Represent semantic relations separately, for example:

    amazon_ec2 --part_of--> aws

Possible relation types:

    alias_of
    is_a
    part_of
    broader_than
    implies
    related_to

Do not automatically make all graph relations bidirectional.

Example:

    EC2 -> AWS

may be a valid broader capability inference.

But:

    AWS -> EC2

is invalid.

Any inference that contributes to scoring must be visible in output evidence.

==================================================
16. FUZZY MATCHING
==================================================

Fuzzy matching must NOT be the primary matcher.

Use it only after exact matching and candidate filtering.

RapidFuzz may be used.

Consider:
- Levenshtein;
- Jaro-Winkler only when appropriate;
- token-based comparisons only with strict safeguards.

Important rules:

Short technical tokens must generally be exact-only.

For example:

    Go
    Git
    R
    C
    C#
    C++
    F#

must not participate in unrestricted fuzzy matching.

Prevent false positives such as:

    Git -> Get
    Go -> Google
    Go -> ordinary English verb "go"

For short tokens, exact matching plus context rules is preferred.

Punctuation-heavy technical technologies should usually have:

    fuzzy_enabled = false

==================================================
17. AMBIGUOUS SKILLS
==================================================

Some exact matches are still ambiguous.

Examples:

    Go
    React
    Spring
    Rust
    Ruby
    Swift
    Chef
    Assembly
    R
    C

These require explicit deterministic context policies.

Example:

    Go developer
    Go engineer
    experience with Go
    experience in Go
    written in Go
    Golang

can support the programming-language meaning.

But:

    go live
    ready to go
    go to

must not.

The architecture should support per-skill ambiguity/context rules.

==================================================
18. YEARS OF EXPERIENCE
==================================================

Parse deterministic expressions such as:

    3+ years
    minimum 5 years
    at least 5 years
    5 years of Python

and common Czech equivalents.

Separate:

    overall software-engineering experience

from:

    years with a particular technology

Never infer technology-specific years from total career length.

My overall professional programmer/developer career started in 2015.

Use the Master file if it contains more precise dates.

==================================================
19. HARD GATES
==================================================

Hard blockers must be evaluated BEFORE interpreting the numeric score.

Potential hard gates include:

- mandatory language unavailable;
- mandatory degree where no equivalent-experience route exists;
- mandatory current geographic/residence condition that cannot be met;
- explicitly mandatory certification that is absent;
- central/core technology with verified level NONE;
- other explicitly non-negotiable requirements.

Important:

Optional requirements must NOT create hard blockers.

For Czech jobs:

Israeli citizenship alone must NOT create a work-permit blocker because:

    labor_market_access = FREE_ACCESS

Residence requirements remain separate.

If status is uncertain, report:

    UNKNOWN / NEEDS REVIEW

rather than fabricating a blocker.

==================================================
20. FIT SCORE
==================================================

Start the design around an explainable 0-100 score.

Use the following as the initial candidate weighting:

    50% Mandatory technical requirements
    20% Core responsibility match
    10% Seniority / years / ownership
    10% Domain relevance
     5% Location / work-model / legal compatibility
     5% Preferred / nice-to-have / ATS signal

Do not accept these blindly.

In the PLAN:
- analyze these weights;
- identify weaknesses;
- propose any justified modification;
- keep the result deterministic;
- make weights configurable.

The score must not hide blockers.

Example:

    score = 86
    blocker = mandatory Czech C1

must NOT produce:

    EXCELLENT FIT

The decision layer must evaluate blockers independently.

==================================================
21. CONFIDENCE SCORE
==================================================

Fit Score and Confidence Score are separate concepts.

Example:

    Fit: 78
    Confidence: 95

means:

    the profile appears to match at about 78%, and the engine has strong evidence.

But:

    Fit: 78
    Confidence: 52

means:

    many relevant requirements could not be verified from the Master profile.

Confidence should consider factors such as:

- how many mandatory requirements are VERIFIED;
- how many are UNKNOWN;
- parser confidence;
- whether job sections were recognized;
- whether requirements had to fall back to ambiguous rules;
- whether fuzzy matching contributed.

Do not artificially increase confidence based on the Fit Score.

==================================================
22. DECISION LABELS
==================================================

Propose deterministic labels such as:

    EXCELLENT_FIT
    GOOD_FIT
    BORDERLINE
    WEAK_FIT
    DO_NOT_APPLY
    MANUAL_REVIEW

Thresholds must be configurable.

Hard blockers should be able to override a high numeric score.

The report should explain the reason.

==================================================
23. OUTPUT
==================================================

Human-readable report should contain at minimum:

    Company
    Position
    Location
    LinkedIn Job ID
    Fit Score
    Confidence Score
    Decision

    Strong matches
    Partial matches
    Verified missing skills
    Unknown/unverified requirements
    Optional gaps
    Hard blockers
    Legal/location notes
    Recommendation

For each important result preserve evidence such as:

    skill_id
    canonical_skill
    matched_job_text
    candidate_level
    required_level
    requirement_type
    matching_method
    score_contribution
    source span / original sentence
    taxonomy inference if any

Also support JSON output for future automation.

==================================================
24. EXAMPLE OUTPUT BEHAVIOUR
==================================================

A result should conceptually resemble:

    FIT SCORE: 78/100
    CONFIDENCE: 89%
    DECISION: GOOD_FIT

    Strong:
      Python
      PostgreSQL
      Flask
      Linux
      developer tooling

    Partial:
      Docker
      GitLab CI/CD

    Unknown:
      SQLAlchemy
      SQLite depth
      Sphinx

    Optional gaps:
      C++
      React
      embedded development

    Blockers:
      None

    Czech labour market:
      FREE_ACCESS

    Residence:
      separate authorization required

Do not hard-code this example or its scores.

It illustrates expected semantics only.

==================================================
25. PERFORMANCE
==================================================

Initial target:

    thousands of job descriptions
    1,000+ canonical skills/aliases

Do not prematurely optimize.

Plan for:

- taxonomy/matcher compilation once;
- aliases loaded once;
- batch processing;
- no SQLite lookup per token;
- PhraseMatcher exact layer;
- candidate filtering before fuzzy comparisons;
- optional multiprocessing only after profiling.

If later benchmarks justify it, consider:
- Aho-Corasick;
- process pools;
- joblib;
- RapidFuzz batch APIs.

Do not introduce them without measured need.

Provide benchmark strategy in the plan.

==================================================
26. SECURITY / NETWORK BEHAVIOUR
==================================================

The program processes untrusted job-page content.

Therefore:

- never execute extracted HTML/JavaScript;
- use reasonable HTTP timeouts;
- validate URLs;
- limit response size;
- do not follow arbitrary unsupported schemes;
- do not write outside expected cache/output directories;
- do not store cookies/passwords/tokens unless an approved design explicitly requires it;
- do not circumvent LinkedIn restrictions.

==================================================
27. TESTING REQUIREMENTS
==================================================

Testing is a first-class requirement.

The plan must include:

A. URL tests
    LinkedIn numeric ID
    slug + numeric ID
    invalid host
    malformed URL

B. normalization tests
    C
    C++
    C#
    .NET
    ASP.NET
    Node.js
    CI/CD
    Objective-C

C. exact matching tests

D. multi-word skill tests

E. taxonomy tests

F. ambiguity tests
    "Go developer" -> Go language
    "ready to go live" -> NOT Go language

    "Git experience" -> Git
    "Get the data" -> NOT Git

G. fuzzy tests

H. skill-state tests
    NONE != UNKNOWN

I. depth tests

J. ANY / ALL / COMPOSITE requirement tests

K. years tests

L. Czech FREE_ACCESS legal-status tests

M. residence-status tests

N. score calculation tests

O. blocker override tests

P. confidence tests

Q. full end-to-end fixture tests using saved job HTML/text.

Tests must not depend on live LinkedIn access.

Use recorded/local sanitized fixtures for parser tests.

==================================================
28. OBSERVABILITY / EXPLAINABILITY
==================================================

Every decision affecting Fit Score must be traceable.

Avoid opaque functions that only return a number.

I must be able to answer:

    Why is this job 74 and that job 81?

For each score component expose:

    maximum points
    awarded points
    matched evidence
    penalty/reason
    unknown information

Prefer deterministic structured evidence over verbose logging.

==================================================
29. PROJECT QUALITY
==================================================

Use:
- modern Python;
- type hints;
- small cohesive modules;
- pathlib;
- dataclasses or the project's existing data-model approach;
- pytest if the project already uses it or if no test framework exists;
- structured exceptions;
- deterministic configuration.

Follow existing project style before introducing new conventions.

Avoid:
- giant classes;
- giant regex files embedded in Python if configuration is better;
- duplicated aliases;
- magic numeric constants spread across modules;
- unnecessary framework dependencies;
- hidden mutable global state;
- broad refactors.

==================================================
30. PHASE 1 OUTPUT — MUST BE IN RUSSIAN
==================================================

Your FIRST response must contain ONLY analysis and a proposed plan.

Write it in Russian.

Do not implement anything.

The plan must contain these sections:

1. Что уже есть в репозитории
   - relevant files;
   - Master Skills source;
   - current dependencies;
   - existing useful code.

2. Что является источником истины
   - Master profile;
   - career start = 2015;
   - Czech FREE_ACCESS;
   - obsolete LinkedIn skill entry must be ignored.

3. Предлагаемая архитектура
   - modules;
   - dependencies;
   - data flow.

4. Модель данных
   - JobPosting;
   - Requirement;
   - Skill;
   - profile/legal status;
   - FitResult.

5. LinkedIn extraction strategy
   - URL;
   - retrieval;
   - JSON-LD;
   - HTML fallback;
   - offline fallback;
   - cache.

6. Requirement parsing strategy
   - sections;
   - EN/CS rules;
   - modalities;
   - years;
   - ANY/ALL/COMPOSITE.

7. Skill matching strategy
   - normalization;
   - aliases;
   - PhraseMatcher;
   - taxonomy;
   - ambiguity;
   - fuzzy fallback.

8. Scoring model
   - exact proposed formula;
   - component weights;
   - level calculations;
   - missing vs unknown;
   - hard blockers;
   - confidence.

9. Czech legal-status handling
   - FREE_ACCESS;
   - work permit;
   - residence authorization;
   - sponsorship ambiguity.

10. CLI/API proposal

11. Exact list of files you propose to create/change

12. Tests
   - unit;
   - regression;
   - parser fixtures;
   - integration.

13. Performance considerations

14. Risks and weak points
   - especially LinkedIn page stability;
   - ambiguous natural language;
   - taxonomy quality;
   - score calibration.

15. Implementation stages
   - small ordered milestones;
   - test/verification after each milestone.

16. Questions/assumptions requiring my approval
   - only material architectural decisions;
   - do not ask questions already answerable from repository files or this specification.

17. Definition of Done

At the very end write:

    ЖДУ ПОДТВЕРЖДЕНИЯ ПЛАНА. РЕАЛИЗАЦИЮ НЕ НАЧИНАЮ.

Then stop.

Do not modify files until I approve the plan.