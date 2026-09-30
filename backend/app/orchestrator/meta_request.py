"""Requests to Henry himself — not answers (same nature as the pace policy, I1-H6).

"How would you rate that?", "Can we switch to Russian?", "Where should I start?"
are addressed to the interviewer, not answers to his question. Sent to the
orchestrator as answers, they spend a follow-up or a whole question and leave
Henry asking about a story nobody told. So they are caught before it, by code:
classification is structure, and structure is owned by code, not by the model.
"""

import re
from collections.abc import Callable
from enum import StrEnum

#: Short utterances only, as with pace: a full answer that merely mentions a
#: rating or a language must stay an answer. A false positive costs more than a
#: miss — a real answer would vanish from the transcript — so the bar is low.
MAX_REQUEST_WORDS = 14


class MetaRequest(StrEnum):
    SCORE = "score"
    LANGUAGE = "language"
    WHERE_TO_START = "where_to_start"


#: ⚠ Every pattern needs the shape of a REQUEST, not a keyword: «Our reply rate was
#: fifteen percent, and that was good» and «I talk to Russian clients daily» are
#: short, contain «rate» and «Russian» — and they are answers.
_LANGS = r"(?:russian|ukrainian|german|spanish|french|chinese|another language|my language)"
_PATTERNS: tuple[tuple[re.Pattern[str], MetaRequest], ...] = (
    (
        re.compile(r"\b(?:how|can|could|would|will) you (?:rate|score|grade|mark|evaluate)\b"),
        MetaRequest.SCORE,
    ),
    (re.compile(r"\b(?:rate|score|grade|mark) (?:my|that|this|the) answer\b"), MetaRequest.SCORE),
    (re.compile(r"\bgive me (?:a|your) (?:score|grade|mark|rating)\b"), MetaRequest.SCORE),
    (re.compile(r"\bwhat(?:'s| is| would be) my (?:score|grade|rating|mark)\b"), MetaRequest.SCORE),
    (re.compile(r"\bout of (?:ten|10)\s*\?\s*$"), MetaRequest.SCORE),
    (re.compile(r"\bhow (?:did|am) i do(?:ing)?(?: so far)?\s*\?"), MetaRequest.SCORE),
    (
        re.compile(
            r"\b(?:can|could|shall|may) (?:we|i) (?:switch|change|move|speak|talk|continue|go on|answer)\b.*\b"
            + _LANGS
            + r"\b"
        ),
        MetaRequest.LANGUAGE,
    ),
    (re.compile(r"\b(?:switch|change) (?:to|into) " + _LANGS + r"\b"), MetaRequest.LANGUAGE),
    (
        re.compile(r"\blet'?s (?:switch|speak|talk|continue) (?:in|to|into) " + _LANGS + r"\b"),
        MetaRequest.LANGUAGE,
    ),
    (re.compile(r"\bwhere (?:should|do|shall) i (?:start|begin)\b"), MetaRequest.WHERE_TO_START),
    (re.compile(r"\bhow should i (?:start|begin|structure)\b"), MetaRequest.WHERE_TO_START),
    (re.compile(r"\bwhat should i (?:start|begin|lead) with\b"), MetaRequest.WHERE_TO_START),
)


def detect(text: str) -> MetaRequest | None:
    """Return the request to Henry in this utterance, or None if it is an answer."""
    if len(text.split()) > MAX_REQUEST_WORDS:
        return None
    lowered = text.lower()
    for pattern, request in _PATTERNS:
        if pattern.search(lowered):
            return request
    return None


def last_question(line: str) -> str:
    """The question to come back to after a refusal: the last one in Henry's line.

    Replaying the whole line would repeat its acknowledgement too («That sounds
    impressive.») — praise said twice sounds scripted. A line without «?» ends
    with its prompt («Walk me through…»), so its last sentence is the question.
    """
    sentences = [s for s in re.split(r"(?<=[.!?])\s+", line.strip()) if s]
    for sentence in reversed(sentences):
        if sentence.endswith("?"):
            return sentence
    return sentences[-1] if sentences else ""


#: Ответ на просьбу — шаблон из `data/prompts/templates`. Отказ (оценка, смена
#: языка) возвращает к последнему вопросу, чтобы разговор не потерял нить; совет
#: «с чего начать» сам приглашает отвечать — вопрос только что прозвучал.
TEMPLATES = {
    MetaRequest.SCORE: "meta_score",
    MetaRequest.LANGUAGE: "meta_language",
    MetaRequest.WHERE_TO_START: "meta_where_to_start",
}
_BACK_TO_QUESTION = {MetaRequest.SCORE, MetaRequest.LANGUAGE}


def reply(request: MetaRequest, template: Callable[[str], str], last_line: str) -> list[str]:
    """What Henry says to a request: a fixed line, then — for a refusal — his question.

    The refusal is a template, not a model call: relying on the model to decline
    a score would make the contract (I1-H1, I1-H3) a hope instead of a rule.
    """
    lines = [template(TEMPLATES[request])]
    if request in _BACK_TO_QUESTION:
        lines.append(last_question(last_line))
    return [line for line in lines if line]
