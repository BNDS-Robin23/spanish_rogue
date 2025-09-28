from __future__ import annotations
from dataclasses import dataclass
from typing import List, Tuple, Optional

from .models import RuleCard, Question
from .lexicon import VerbLexicon


@dataclass(frozen=True)
class PresentRule:
    person: str
    stem_from: Optional[str]
    stem_to: Optional[str]
    ending_from: Optional[str]
    ending_to: Optional[str]

    @property
    def pattern(self) -> str:
        parts = []
        if self.stem_from is not None or self.stem_to is not None:
            parts.append(f"{self.stem_from or ''}->{self.stem_to or ''}")
        if self.ending_from is not None or self.ending_to is not None:
            parts.append(f"{self.ending_from or ''}->{self.ending_to or ''}")
        return " + ".join(parts)


PERSONS = [
    "直陈式现在时+第一人称单数",
    "直陈式现在时+第二人称单数",
    "直陈式现在时+第三人称单数",
    "直陈式现在时+第一人称复数",
    "直陈式现在时+第二人称复数",
    "直陈式现在时+第三人称复数",
]

REGULAR_ENDINGS = {
    "ar": ["o", "as", "a", "amos", "áis", "an"],
    "r": [],
    "er": ["o", "es", "e", "emos", "éis", "en"],
    "ir": ["o", "es", "e", "imos", "ís", "en"],
}


def present_indicative_rules(lexicon: Optional[VerbLexicon] = None) -> List[RuleCard]:
    rules: List[RuleCard] = []
    for base, endings in (e for e in REGULAR_ENDINGS.items() if e[0] in ("ar", "er", "ir")):
        for i, to in enumerate(endings):
            rules.append(RuleCard(
                person=PERSONS[i],
                stem_from=None,
                stem_to=None,
                ending_from=base,
                ending_to=to,
            ))
    if lexicon is not None and lexicon.verbs:
        for v in lexicon.verbs:
            inf = v.get("infinitive")
            if not inf:
                continue
            forms = v.get("present_indicative", {}) or {}
            if inf.endswith("ar"):
                base = "ar"
            elif inf.endswith("er"):
                base = "er"
            elif inf.endswith("ir"):
                base = "ir"
            else:
                base = inf[-2:]
            stem = inf[: -len(base)]
            regular = REGULAR_ENDINGS.get(base, [])
            for i, person in enumerate(PERSONS):
                target = forms.get(person)
                if not target:
                    continue
                ending_prime = None
                for e in sorted(set(REGULAR_ENDINGS.get(base, [])), key=len, reverse=True):
                    if target.endswith(e):
                        ending_prime = e
                        break
                if ending_prime is None:
                    ending_prime = target[-2:]
                stem_prime = target[: -len(ending_prime)] if ending_prime else target

                stem_from = stem if stem_prime != stem else None
                stem_to = stem_prime if stem_prime != stem else None
                ending_from = base
                ending_to = ending_prime

                rules.append(RuleCard(
                    person=person,
                    stem_from=stem_from,
                    stem_to=stem_to,
                    ending_from=ending_from,
                    ending_to=ending_to,
                    verb_infinitive=inf,
                ))
    return rules


def detect_ending(infinitive: str) -> str:
    for e in ("ar", "er", "ir"):
        if infinitive.endswith(e):
            return e
    return ""


def apply_rule_to_verb(infinitive: str, rule: RuleCard) -> Tuple[bool, str]:
    if rule.verb_infinitive and rule.verb_infinitive != infinitive:
        return False, infinitive

    ending = detect_ending(infinitive)
    if not ending:
        return False, infinitive

    stem = infinitive[: -len(ending)]

    if rule.ending_from is not None and rule.ending_from not in ("ar", "er", "ir"):
        return False, infinitive
    if rule.ending_from is not None and rule.ending_from != ending:
        return False, infinitive

    new_stem = stem
    if rule.stem_from is not None or rule.stem_to is not None:
        if rule.stem_from is not None and stem != rule.stem_from:
            return False, infinitive
        new_stem = rule.stem_to if rule.stem_to is not None else stem

    new_ending = ending
    if rule.ending_to is not None:
        new_ending = rule.ending_to

    return True, f"{new_stem}{new_ending}"


def expected_present_form(infinitive: str, person: str, lexicon: Optional[VerbLexicon] = None) -> str:
    if lexicon is not None:
        form = lexicon.get_present_form(infinitive, person)
        if form:
            return form
    ending = detect_ending(infinitive)
    if ending in ("ar", "er", "ir"):
        try:
            idx = PERSONS.index(person)
        except ValueError:
            return ""
        stem = infinitive[: -len(ending)]
        endings = REGULAR_ENDINGS.get(ending, [])
        if 0 <= idx < len(endings):
            return f"{stem}{endings[idx]}"
    return ""


def random_question() -> Question:
    import random

    return Question(person=random.choice(PERSONS))
