"""Sentence-gated runtime enforcer (doc 13 "Runtime pipeline").

Per-sentence checks are monotone: a spoken prefix stays compliant whatever comes
next. The only turn-level check (question_or_ack) is additively recoverable —
the turn runner appends a seed question instead of retracting speech.
"""

import re
from dataclasses import dataclass
from typing import Any, ClassVar

from app.contracts.spec import ContractSpec, RuleSpec

_CYRILLIC = re.compile(r"[Ѐ-ӿ]")
_WORD = re.compile(r"[A-Za-z']+")
_QREF = re.compile(r"\bQ(\d{1,2})\b", re.IGNORECASE)


@dataclass(frozen=True)
class Violation:
    rule_id: str
    check: str
    severity: str
    sentence_index: int  # -1 for turn-level
    matched: str = ""


@dataclass
class TurnContext:
    state: str = ""  # orchestrator state, e.g. CORE_QUEST
    question_count: int = 0  # for quoted_question_in_transcript (Mode 2)


class TurnEnforcer:
    """Tracks one agent turn; feed() sentences as they stream, finish() at stream end.

    Обычный класс, а не `@dataclass`, — ради мутационного гейта: mutmut 3.7 не
    мутирует ни одного метода в декорированном классе, и под `@dataclass` здесь
    молчали все проверки контракта (70 из 88 строк функций модуля).
    """

    def __init__(self, spec: ContractSpec, ctx: TurnContext) -> None:
        self.spec = spec
        self.ctx = ctx
        self.sentences: list[str] = []
        self._chars = 0

    def feed(self, sentence: str) -> Violation | None:
        """Validate the next sentence BEFORE it reaches TTS. None = safe to speak."""
        index = len(self.sentences)
        for rule in self.spec.runtime_rules():
            violation = self._check_sentence(rule, sentence, index)
            if violation is not None:
                return violation
        self.sentences.append(sentence)
        self._chars += len(sentence) + 1
        return None

    def finish(self) -> Violation | None:
        """Turn-level checks after the stream ends (additively recoverable)."""
        for rule in self.spec.runtime_rules():
            if rule.check == "question_or_ack":
                violation = self._check_question_or_ack(rule)
                if violation is not None:
                    return violation
        return None

    def spoken_text(self) -> str:
        return " ".join(self.sentences)

    # Раньше это был плоский if/elif на пять веток со сложностью 13 при пороге 10,
    # и он держался снимком гейта с пометкой «дробить нельзя, критический путь по
    # doc 13, constitution §7». Пометка ссылалась на §7 неточно: §7 запрещает
    # переизобретать РЕШЕНИЯ из docs/00–20, а не менять форму кода. Ни одна
    # проверка контракта здесь не изменилась — только разложены по методам,
    # поведение то же и покрыто тестами контрактов (100%).
    def _check_sentence(self, rule: RuleSpec, sentence: str, index: int) -> Violation | None:
        check = self._CHECKS.get(rule.check)
        return None if check is None else check(self, rule, sentence, index)

    def _no_cyrillic(self, rule: RuleSpec, sentence: str, index: int) -> Violation | None:
        match = _CYRILLIC.search(sentence)
        return self._violation(rule, index, match.group()) if match else None

    def _forbid_patterns(self, rule: RuleSpec, sentence: str, index: int) -> Violation | None:
        lowered = sentence.lower()
        for pattern in self.spec.forbidden_patterns:
            if pattern in lowered:
                return self._violation(rule, index, pattern)
        return None

    def _max_sentences(self, rule: RuleSpec, sentence: str, index: int) -> Violation | None:
        if index >= int(rule.params["max"]):
            return self._violation(rule, index, f"sentence {index + 1}")
        return None

    def _max_chars_cumulative(self, rule: RuleSpec, sentence: str, index: int) -> Violation | None:
        total = self._chars + len(sentence)
        if total > int(rule.params["max"]):
            return self._violation(rule, index, f"{total} chars")
        return None

    def _quoted_question(self, rule: RuleSpec, sentence: str, index: int) -> Violation | None:
        for ref in _QREF.finditer(sentence):
            number = int(ref.group(1))
            if number < 1 or number > self.ctx.question_count:
                return self._violation(rule, index, ref.group())
        return None

    # Таблица объявлена ПОСЛЕ методов: имена должны существовать к моменту
    # создания класса. Неизвестный `check` — не ошибка: контракт может нести
    # правило, которого этот enforcer не знает, и тогда оно просто не проверяется
    # здесь (так же вело себя прежнее if/elif, падавшее в `return None`).
    # ClassVar — таблица одна на класс, а не поле экземпляра.
    _CHECKS: ClassVar[dict[str, Any]] = {
        "no_cyrillic": _no_cyrillic,
        "forbid_patterns": _forbid_patterns,
        "max_sentences": _max_sentences,
        "max_chars_cumulative": _max_chars_cumulative,
        "quoted_question_in_transcript": _quoted_question,
    }

    def _check_question_or_ack(self, rule: RuleSpec) -> Violation | None:
        states = [str(s) for s in rule.params.get("states", [])]
        if states and self.ctx.state not in states:
            return None
        text = self.spoken_text()
        if "?" in text:
            return None
        words = _WORD.findall(text.lower())
        max_words = int(rule.params.get("ack_max_words", 12))
        is_short = 0 < len(words) <= max_words
        whitelist = self.spec.ack_whitelist
        is_ack = any(ack in text.lower() for ack in whitelist) if whitelist else False
        if is_short and is_ack:
            return None
        return self._violation(rule, -1, "no question and not a short ack")

    @staticmethod
    def _violation(rule: RuleSpec, index: int, matched: str) -> Violation:
        return Violation(
            rule_id=rule.rule_id,
            check=rule.check,
            severity=rule.severity,
            sentence_index=index,
            matched=matched,
        )


class ContractEnforcer:
    """Factory bound to one loaded contract; validates whole texts for retries too."""

    def __init__(self, spec: ContractSpec) -> None:
        self.spec = spec

    def start_turn(self, ctx: TurnContext) -> TurnEnforcer:
        return TurnEnforcer(spec=self.spec, ctx=ctx)

    def violation_event(
        self, violation: Violation, *, turn_index: int, state: str, recovery: str, recovered: bool
    ) -> dict[str, Any]:
        """Doc 13 violation event schema — recorded pre-recovery (transparency effect)."""
        return {
            "turn_index": turn_index,
            "state": state,
            "constraint_id": violation.rule_id,
            "severity": violation.severity,
            "sentence_index": violation.sentence_index,
            "matched": violation.matched,
            "recovery": recovery,
            "recovered": recovered,
        }
