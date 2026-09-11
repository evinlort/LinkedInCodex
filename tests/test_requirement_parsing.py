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
        )
    )
    matcher = SkillMatcher(load_skill_definitions())
    attached = [matcher.attach(item) for item in requirements]
    assert [item.expression_op for item in attached] == [
        ExpressionOp.ANY,
        ExpressionOp.ALL,
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
