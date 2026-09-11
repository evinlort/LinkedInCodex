from __future__ import annotations

import re
from dataclasses import replace
from decimal import Decimal

import spacy
from rapidfuzz import fuzz
from spacy.matcher import PhraseMatcher

from jobfit.matching.normalization import punctuation_heavy, rule_normalize
from jobfit.models import (
    ExpressionOp,
    MatchingMethod,
    Requirement,
    ScoreComponent,
    SkillDefinition,
    SkillMention,
    SourceSpan,
)

TOKEN_RE = re.compile(r"[\w.+#/-]+", re.UNICODE)


class SkillMatcher:
    def __init__(self, definitions: tuple[SkillDefinition, ...]) -> None:
        self.definitions = definitions
        self.by_id = {item.id: item for item in definitions}
        self.nlp = spacy.blank("xx")
        self.matcher = PhraseMatcher(self.nlp.vocab, attr="LOWER")
        self.labels: dict[str, SkillDefinition] = {}
        for definition in definitions:
            label = f"SKILL__{definition.id}"
            self.labels[label] = definition
            self.matcher.add(label, [self.nlp.make_doc(alias) for alias in definition.aliases])

    def _context_allows(self, definition: SkillDefinition, text: str, matched: str) -> bool:
        if not definition.ambiguous:
            return True
        folded = text.casefold()
        if any(term in folded for term in definition.negative_context):
            return False
        if matched.casefold() == "golang":
            return True
        return any(term in folded for term in definition.positive_context)

    def find(self, text: str, base_offset: int = 0) -> tuple[SkillMention, ...]:
        doc = self.nlp.make_doc(text)
        candidates: list[SkillMention] = []
        for match_id, start, end in self.matcher(doc):
            label = self.nlp.vocab.strings[match_id]
            definition = self.labels[label]
            token_span = doc[start:end]
            matched = token_span.text
            if not self._context_allows(definition, text, matched):
                continue
            method = (
                MatchingMethod.CONTEXT_EXACT if definition.ambiguous else MatchingMethod.EXACT
            )
            candidates.append(
                SkillMention(
                    skill_id=definition.id,
                    canonical_name=definition.canonical_name,
                    span=SourceSpan(
                        base_offset + token_span.start_char,
                        base_offset + token_span.end_char,
                        matched,
                    ),
                    method=method,
                    matcher_quality=Decimal("0.95") if definition.ambiguous else Decimal("1"),
                )
            )
        # Longest match wins for overlapping aliases; exact duplicates become one result.
        ordered = sorted(
            candidates,
            key=lambda item: (-(item.span.end - item.span.start), item.span.start),
        )
        selected: list[SkillMention] = []
        for candidate in ordered:
            overlaps = any(
                candidate.span.start < item.span.end and item.span.start < candidate.span.end
                for item in selected
            )
            duplicate = any(
                candidate.skill_id == item.skill_id
                and candidate.span.start == item.span.start
                and candidate.span.end == item.span.end
                for item in selected
            )
            if not overlaps and not duplicate:
                selected.append(candidate)

        if not selected:
            selected.extend(self._fuzzy_find(text, base_offset))
        return tuple(sorted(selected, key=lambda item: item.span.start))

    def _fuzzy_find(self, text: str, base_offset: int) -> list[SkillMention]:
        tokens = [(match.group(), match.start(), match.end()) for match in TOKEN_RE.finditer(text)]
        results: list[SkillMention] = []
        for definition in self.definitions:
            if not definition.fuzzy_enabled:
                continue
            for alias in definition.aliases:
                if len(alias) < 5 or punctuation_heavy(alias):
                    continue
                alias_words = len(alias.split())
                for index in range(0, len(tokens) - alias_words + 1):
                    group = tokens[index : index + alias_words]
                    surface = text[group[0][1] : group[-1][2]]
                    left = rule_normalize(surface)
                    right = rule_normalize(alias)
                    if not left or left[0] != right[0] or abs(len(left) - len(right)) > 1:
                        continue
                    if fuzz.ratio(left, right) < 95:
                        continue
                    results.append(
                        SkillMention(
                            skill_id=definition.id,
                            canonical_name=definition.canonical_name,
                            span=SourceSpan(
                                base_offset + group[0][1],
                                base_offset + group[-1][2],
                                surface,
                            ),
                            method=MatchingMethod.FUZZY,
                            matcher_quality=Decimal("0.60"),
                        )
                    )
        return results

    def attach(self, requirement: Requirement) -> Requirement:
        mentions = self.find(requirement.raw_text, requirement.span.start)
        folded = requirement.raw_text.casefold()
        if len(mentions) > 1 and (
            re.search(r"\b(?:or|nebo)\b", folded) or "/" in requirement.raw_text
        ):
            op = ExpressionOp.ANY
        elif len(mentions) > 1 and any(term in folded for term in ("such as", "e.g.", "např.")):
            op = ExpressionOp.COMPOSITE
        elif len(mentions) > 1 and ("," in requirement.raw_text or re.search(r"\band\b", folded)):
            op = ExpressionOp.ALL
        elif mentions or requirement.minimum_years is not None or any(
            term in folded
            for term in (
                "work permit",
                "eligible to work",
                "right to work",
                "sponsorship",
                "visa",
                "residence",
                "citizenship",
                "english",
                "czech",
                "degree",
            )
        ):
            op = ExpressionOp.ATOM
        else:
            op = ExpressionOp.REVIEW
        component = requirement.component
        if mentions and all(self.by_id[item.skill_id].category == "domain" for item in mentions):
            component = ScoreComponent.DOMAIN
        return replace(
            requirement,
            mentions=mentions,
            component=component,
            expression_op=op,
            review_reason=(
                "No deterministic requirement rule matched"
                if op is ExpressionOp.REVIEW
                else None
            ),
        )
