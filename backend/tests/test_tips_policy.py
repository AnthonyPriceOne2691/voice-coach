"""Решение о заметке к речи (D3a.2): модель предлагает кандидата, решает код.

Контракт — настоящий `talk.contract.yaml`: заметка проходит тот же енфорсер, что
реплики Генри, и тест обязан это видеть, а не подставную лямбду.
"""

import json
from pathlib import Path

import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.contracts.enforcer import ContractEnforcer
from app.contracts.spec import load_contract
from app.orchestrator.tips import (
    MAX_FRAGMENT_WORDS,
    Candidate,
    NoteKind,
    Rejection,
    contract_gate,
    decide,
    parse_candidate,
    words,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
PASSES = contract_gate(
    ContractEnforcer(load_contract(REPO_ROOT / "data" / "contracts" / "talk.contract.yaml"))
)

C2_SAID = "Yesterday I go to the office and meet my client."
C2 = Candidate(
    NoteKind.ERROR,
    "I go to the office and meet my client",
    "I went to the office and met my client",
    "past tense",
)


def _raw(kind: str, said: str = "", better: str = "", why: str = "") -> str:
    return json.dumps({"kind": kind, "said": said, "better": better, "why": why})


def test_error_in_what_was_said_becomes_a_note() -> None:
    """C2: ошибка в распознанном — заметка с дословным фрагментом и причиной."""
    note = decide(C2, C2_SAID, seen=[], passes_contract=PASSES)
    assert note == {
        "kind": "error",
        "said": "I go to the office and meet my client",
        "better": "I went to the office and met my client",
        "why": "past tense",
        "spoken": False,
    }


def test_poor_phrase_becomes_a_style_note() -> None:
    """C3: правильная, но плоская фраза — заметка о бедной речи."""
    said = "The trip was good. The hotel was good and the food was very good."
    candidate = Candidate(
        NoteKind.STYLE, "the food was very good", "the food was delicious", "more vivid"
    )
    note = decide(candidate, said, seen=[], passes_contract=PASSES)
    assert not isinstance(note, Rejection)
    assert (note["kind"], note["said"], note["why"]) == (
        "style",
        "the food was very good",
        "more vivid",
    )


def test_fragment_is_stored_as_recognized_not_as_quoted_by_the_model() -> None:
    """C2: модель процитировала другим регистром и с запятой — в заметку идёт распознанное."""
    candidate = Candidate(
        NoteKind.ERROR, "i go to the office, and meet my client", C2.better, C2.why
    )
    note = decide(candidate, C2_SAID, seen=[], passes_contract=PASSES)
    assert not isinstance(note, Rejection)
    assert note["said"] == "I go to the office and meet my client"


@pytest.mark.parametrize(
    "said",
    [
        "I goes to work every day",  # C6: таких слов в реплике нет
        "go to the off",  # часть слова — не слово
    ],
)
def test_words_that_were_not_said_are_never_corrected(said: str) -> None:
    """C6: фрагмента нет в распознанном — код отбрасывает кандидата."""
    candidate = Candidate(NoteKind.ERROR, said, "I went to the office", "")
    assert decide(candidate, C2_SAID, seen=[], passes_contract=PASSES) is Rejection.NOT_SAID


def test_same_correction_later_is_not_noted_again() -> None:
    """C7: та же поправка позже снова — второй заметки нет (по фрагменту и по варианту)."""
    first = decide(C2, C2_SAID, seen=[], passes_contract=PASSES)
    assert not isinstance(first, Rejection)
    assert decide(C2, C2_SAID, seen=[first], passes_contract=PASSES) is Rejection.REPEAT
    other_said = Candidate(NoteKind.ERROR, "and meet my client", C2.better, "")
    assert decide(other_said, C2_SAID, seen=[first], passes_contract=PASSES) is Rejection.REPEAT


def test_change_of_case_or_punctuation_only_is_not_a_correction() -> None:
    """C1: «исправление» без смены слов — не заметка."""
    candidate = Candidate(NoteKind.STYLE, "I went to the gym", "I went to the gym!", "")
    said = "I went to the gym this morning and it was packed."
    assert decide(candidate, said, seen=[], passes_contract=PASSES) is Rejection.UNCHANGED


def test_retelling_instead_of_a_fragment_is_rejected() -> None:
    """Вариант длиннее предела — это пересказ, а не поправка фрагмента."""
    said = " ".join(["word"] * (MAX_FRAGMENT_WORDS + 1))
    candidate = Candidate(NoteKind.STYLE, said, said + " indeed", "")
    assert decide(candidate, said, seen=[], passes_contract=PASSES) is Rejection.TOO_LONG


@pytest.mark.parametrize(
    "better",
    [
        "Я пошёл в офис и встретил клиента",  # кириллица — I3-H1
        "我去了办公室",  # иероглифы: I3-H1 их не режет, а заметка обязана быть английской
    ],
)
def test_variant_that_is_not_english_is_rejected_as_contract(better: str) -> None:
    """Вариант не по-английски — не заметка, и причина названа верно (не «не меняет слов»)."""
    candidate = Candidate(NoteKind.ERROR, C2.said, better, "")
    assert decide(candidate, C2_SAID, seen=[], passes_contract=PASSES) is Rejection.CONTRACT


@pytest.mark.parametrize(
    "why",
    [
        "this is a much more natural phrase",  # длиннее пяти слов
        "B1 level",  # оценка уровня — I3-H2
    ],
)
def test_bad_reason_is_dropped_but_the_note_stays(why: str) -> None:
    """Причина не прошла — заметка остаётся без причины, а не пропадает."""
    candidate = Candidate(NoteKind.ERROR, C2.said, C2.better, why)
    note = decide(candidate, C2_SAID, seen=[], passes_contract=PASSES)
    assert not isinstance(note, Rejection)
    assert note["why"] == ""


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (_raw("none"), Rejection.NONE),  # C1, C4: модель ничего не нашла
        ("Sure! You could say…", Rejection.MALFORMED),  # проза вместо JSON
        (json.dumps(["error"]), Rejection.MALFORMED),
        (_raw("grade", "a", "b"), Rejection.MALFORMED),
        (json.dumps({"kind": "error", "said": "a"}), Rejection.MALFORMED),
        (_raw("error", "", "better"), Rejection.MALFORMED),
    ],
)
def test_anything_but_a_candidate_is_a_rejection_not_an_exception(
    raw: str, expected: Rejection
) -> None:
    """C1, C4: «ничего» и мусор — отказ с причиной, а не падение хода."""
    assert parse_candidate(raw) is expected


def test_candidate_is_parsed_from_the_schema_answer() -> None:
    """C2: ответ по схеме — кандидат с полями без пробелов по краям."""
    parsed = parse_candidate(_raw("error", " I go ", "I went", " past tense "))
    assert parsed == Candidate(NoteKind.ERROR, "I go", "I went", "past tense")


def test_words_ignore_case_punctuation_and_apostrophe_kind() -> None:
    """Сверка фрагмента не спотыкается о вид апострофа, который ставит распознавание."""
    assert words("Don’t worry, I'm FINE.") == ["don't", "worry", "i'm", "fine"]


def test_mixed_utterance_gives_one_note_about_the_error() -> None:
    """C5: в реплике и ошибка, и бедная фраза — модель отдаёт одного кандидата, код — одну заметку."""
    said = "Yesterday I go to a very good restaurant."
    raw = _raw(
        "error", "I go to a very good restaurant", "I went to a very good restaurant", "past tense"
    )
    candidate = parse_candidate(raw)
    assert isinstance(candidate, Candidate)
    note = decide(candidate, said, seen=[], passes_contract=PASSES)
    assert not isinstance(note, Rejection)
    assert note["kind"] == "error"


# --- свойства (реляционные оракулы, §6.5): ожидаемого значения нет — есть инвариант ---

_LETTERS = st.text(
    alphabet=st.characters(whitelist_categories=("Ll", "Lu"), max_codepoint=127),
    min_size=1,
    max_size=8,
)
_SEPARATORS = st.sampled_from([" ", ", ", ". ", "! ", " — ", "? "])


@st.composite
def _utterance_with_fragment(draw: st.DrawFn) -> tuple[str, list[str]]:
    """Реплика из случайных слов с пунктуацией и кусок её слов подряд (до 19)."""
    said = draw(st.lists(_LETTERS, min_size=2, max_size=25))
    gaps = draw(st.lists(_SEPARATORS, min_size=len(said) - 1, max_size=len(said) - 1))
    text = said[0] + "".join(gap + word for gap, word in zip(gaps, said[1:], strict=True))
    start = draw(st.integers(0, len(said) - 1))
    end = draw(st.integers(start + 1, min(len(said), start + 19)))
    return text, said[start:end]


@given(_utterance_with_fragment(), st.booleans())
def test_note_fragment_is_always_a_verbatim_slice_of_the_utterance(
    sample: tuple[str, list[str]], shout: bool
) -> None:
    """C6 (свойство): как бы модель ни процитировала, в заметку идёт кусок реплики КАК ЕСТЬ."""
    text, fragment = sample
    quoted = " ".join(word.upper() if shout else word.lower() for word in fragment)
    candidate = Candidate(NoteKind.ERROR, quoted, "xylophonezz " + quoted, "")
    note = decide(candidate, text, seen=[], passes_contract=lambda _: True)
    assert not isinstance(note, Rejection)
    assert note["said"] in text
    assert words(note["said"]) == words(quoted)


@given(_utterance_with_fragment())
def test_words_that_were_never_said_are_never_noted(sample: tuple[str, list[str]]) -> None:
    """C6 (свойство): фрагмент со словом, которого в реплике нет, — всегда отказ."""
    text, fragment = sample
    quoted = " ".join([*fragment, "xylophonezz"])  # слово длиннее любого в реплике
    candidate = Candidate(NoteKind.ERROR, quoted, "something better", "")
    assert decide(candidate, text, seen=[], passes_contract=lambda _: True) is Rejection.NOT_SAID
