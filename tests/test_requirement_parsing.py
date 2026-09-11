from jobfit.config import load_skill_definitions
from jobfit.matching import SkillMatcher
from jobfit.models import ExpressionOp, JobPosting, RequirementType
from jobfit.parsing.requirements import parse_requirements, structure_job


def _job(text: str) -> JobPosting:
    return JobPosting("linkedin", "1", "https://www.linkedin.com/jobs/view/1", None, None,
                      None, None, None, text, "hash")


def test_section_context_beats_experience_word() -> None:
    requirements, quality = parse_requirements(
        _job("Requirements:\n- Python\nNice to Have:\n- Experience with C++\n")
    )
    assert requirements[0].requirement_type is RequirementType.MANDATORY
    assert requirements[1].requirement_type is RequirementType.PREFERRED
    assert quality == 1


def test_czech_sections_and_years() -> None:
    requirements, _ = parse_requirements(
        _job("Požadavky:\n- Minimálně 5 let praxe v software development\nVýhodou:\n- Docker\n")
    )
    assert requirements[0].minimum_years == 5
    assert requirements[0].years_subject == "overall"
    assert requirements[1].requirement_type is RequirementType.PREFERRED


def test_boolean_and_composite_expressions() -> None:
    requirements, _ = parse_requirements(
        _job(
            "Requirements:\n"
            "- Flask/FastAPI\n"
            "- PostgreSQL and RabbitMQ\n"
            "- Databases such as PostgreSQL and SQLite\n"
            "- JavaScript, PostgreSQL, .NET / C#, Node.js\n"
        )
    )
    matcher = SkillMatcher(load_skill_definitions())
    attached = [matcher.attach(item) for item in requirements]
    assert [item.expression_op for item in attached] == [
        ExpressionOp.ANY,
        ExpressionOp.ALL,
        ExpressionOp.COMPOSITE,
        ExpressionOp.COMPOSITE,
    ]


def test_job_gets_structured_sections() -> None:
    job = _job(
        "Requirements:\n- Python\nResponsibilities:\n- Build APIs\n"
        "Nice to Have:\n- Docker\nBenefits:\n- Five weeks leave\n"
    )
    requirements, _ = parse_requirements(job)
    structured = structure_job(job, requirements)
    assert structured.mandatory_requirements == ("Python",)
    assert structured.responsibilities == ("Build APIs",)
    assert structured.preferred_requirements == ("Docker",)
    assert structured.benefits == ("Five weeks leave",)


def test_footer_text_stops_active_requirement_section() -> None:
    requirements, _ = parse_requirements(
        _job(
            "Nice to Have:\n- Docker\nFor any questions, send us a message.\n"
            "Our company prohibits discrimination based on age.\n"
        )
    )
    assert [item.raw_text for item in requirements] == ["Docker"]


def test_linkedin_about_you_and_stack_sections() -> None:
    requirements, quality = parse_requirements(
        _job(
            "What You’ll Be Working On\n"
            "- Build backend services\n"
            "💪 About You\n"
            "You have production experience in TypeScript/Node.js or Go\n"
            "- Solid knowledge of PostgreSQL\n"
            "Nice to have:\n"
            "- Docker\n"
            "Our Stack\n"
            "TypeScript, Node.js, Go, PostgreSQL, Docker\n"
            "What We Offer\n"
            "Flexible working hours\n"
        )
    )

    assert quality == 1
    assert [item.requirement_type for item in requirements] == [
        RequirementType.CORE_RESPONSIBILITY,
        RequirementType.MANDATORY,
        RequirementType.MANDATORY,
        RequirementType.PREFERRED,
    ]
    assert [item.raw_text for item in requirements] == [
        "Build backend services",
        "You have production experience in TypeScript/Node.js or Go",
        "Solid knowledge of PostgreSQL",
        "Docker",
    ]

    matcher = SkillMatcher(load_skill_definitions())
    language_requirement = matcher.attach(requirements[1])
    assert language_requirement.expression_op is ExpressionOp.ANY
    assert [item.skill_id for item in language_requirement.mentions] == [
        "typescript",
        "nodejs",
        "go",
    ]


def test_czech_job_sections_and_benefits_are_separate() -> None:
    job = _job(
        "Jakmile se k nám přidáte, budete:\n"
        "Vyvíjet kvalitní a testovaný kód.\n"
        "Používané technologie:\n"
        "JavaScript, PostgreSQL, .NET / C#, Node.js.\n"
        "Místo:\n"
        "Brno\n"
        "Co potřebujete k úspěchu?\n"
        "Minimálně 3 roky relevantní praxe.\n"
        "Velmi dobrou znalost anglického jazyka.\n"
        "Co nabízíme:\n"
        "Možnost práce z domova.\n"
        "Mezi hlavní benefity patří:\n"
        "Pět dnů volna.\n"
        "Sounds good? Send us your CV.\n"
    )

    requirements, quality = parse_requirements(job)
    structured = structure_job(job, requirements)

    assert quality == 1
    assert [item.requirement_type for item in requirements] == [
        RequirementType.CORE_RESPONSIBILITY,
        RequirementType.CORE_RESPONSIBILITY,
        RequirementType.MANDATORY,
        RequirementType.MANDATORY,
    ]
    assert "Brno" not in [item.raw_text for item in requirements]
    assert structured.benefits == ("Možnost práce z domova.", "Pět dnů volna.")
