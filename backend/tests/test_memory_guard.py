"""Что может попасть в память Генри (D3b): модель предлагает кандидатов, решает код.

Правила и список «никогда» — настоящие `data/contracts/memory*`, контракт разговора —
настоящий `talk.contract.yaml`: тест обязан видеть те же данные, что продукт, а не
подставные лямбды. Примеры — синтетика спеки; `data/sessions/` не читается.
"""

import json
import logging
import random
import string
from dataclasses import asdict, replace
from pathlib import Path

import pytest

from app.contracts.enforcer import ContractEnforcer
from app.contracts.spec import ContractError, load_contract
from app.memory.guard import (
    Candidate,
    MemoryKind,
    Reason,
    Rejection,
    Sifted,
    decide,
    is_repeat,
    sift,
)
from app.memory.rules import Category, load_never_store, load_rules
from app.orchestrator.tips import contract_gate, words

CONTRACTS = Path(__file__).resolve().parents[2] / "data" / "contracts"
RULES = load_rules(CONTRACTS)
PASSES = contract_gate(ContractEnforcer(load_contract(CONTRACTS / "talk.contract.yaml")))
TOPIC = MemoryKind.TOPIC

CALL_SAID = "I have a discovery call with an agency on Friday and I'm a bit nervous about it."
CALL = Candidate(
    MemoryKind.PLAN,
    "You have a discovery call with an agency on Friday.",
    "How did the discovery call go?",
    "i have a discovery call with an agency on friday",
)
CALL_KEPT = replace(CALL, evidence="I have a discovery call with an agency on Friday")
DUNE_SAID = "I started reading Dune last week and I can't put it down."
DUNE = Candidate(
    TOPIC, "You started reading Dune last week.", "How is Dune?", "I started reading Dune"
)


def _decide(candidate: Candidate, *said: str, known: tuple[str, ...] = ()) -> object:
    return decide(candidate, said=said, known=known, rules=RULES, passes_contract=PASSES)


def _sift(raw: str, *said: str) -> Sifted | Rejection:
    return sift(raw, said=said, saved=(), rules=RULES, passes_contract=PASSES)


def _raw(*memories: Candidate) -> str:
    return json.dumps({"memories": [asdict(memory) for memory in memories]})


def _table(text: str) -> list[list[str]]:
    """Случаи «колонка | колонка» — по строке на случай: таблица читается глазами."""
    return [[cell.strip() for cell in line.split("|")] for line in text.strip().splitlines()]


def test_note_from_his_own_words_is_kept_with_the_quote_as_recognized() -> None:
    """K2, часть guard: заметка из его слов проходит; цитата — в написании распознанного."""
    assert _decide(CALL, CALL_SAID) == CALL_KEPT


def test_quote_he_did_not_say_or_a_text_about_something_else_is_dropped() -> None:
    """K3: «I love surfing» сказал Генри (его реплик в `said` нет) или никто — отказ (M-H3)."""
    surfing = Candidate(TOPIC, "You love surfing.", "Where do you surf?", "I love surfing")
    assert _decide(surfing, CALL_SAID) == Rejection(Reason.NOT_SAID)
    unrelated = replace(CALL, text="You love surfing in Portugal.")  # цитата его, текст — нет
    assert _decide(unrelated, CALL_SAID) == Rejection(Reason.UNRELATED)


# K4 контакты · K5 деньги · K6 суд · K7 семья и здоровье · K8 Ally. Вторая строка пары —
# цитата, обрезанная до безобидного хвоста: категорию ловит реплика, где цитата стоит.
_NEVER_STORE = _table("""
Send it to anton.dev@example.com | You asked me to send it to anton.dev@example.com. | Did it arrive? | Send it to anton.dev@example.com | contacts
Send it to anton.dev@example.com | You want me to send it over. | Did you get it? | Send it to | contacts
Call me at +7 921 555 01 23 | You gave me your number, +7 921 555 01 23. | Should I call? | Call me at +7 921 555 01 23 | contacts
Call me at +7 921 555 01 23 | You want me to call you. | Did I call? | Call me at | contacts
My hourly rate is 50 dollars | Your hourly rate is 50 dollars. | Is that rate working for you? | My hourly rate is 50 dollars | money
I still owe the bank 300,000 roubles | You still owe the bank a lot. | How is it going? | I still owe the bank | money
I have a court hearing about the contract next week | You have a hearing about the contract next week. | How did it go? | a court hearing about the contract | legal
My daughter caught a cold, so I barely slept | Your daughter caught a cold. | Is she feeling better? | My daughter caught a cold | family,health
My daughter caught a cold, so I barely slept | You barely slept last night. | Did you get some rest? | so I barely slept | family,health
My daughter started school this week | Your daughter started school. | How is school? | My daughter started school | family
I think I caught a cold again | You caught a cold again. | Are you better? | I caught a cold again | health
I spent the weekend working on Smart frend Ally | You spent the weekend working on Smart frend Ally. | How is it going? | working on Smart frend Ally | ally
I spent the weekend working on Smart frend Ally | You spent the weekend working on a side project. | Did you finish it? | I spent the weekend working | ally
""")


@pytest.mark.parametrize(("said", "text", "follow_up", "evidence", "categories"), _NEVER_STORE)
def test_never_store_category_drops_the_whole_candidate(
    said: str, text: str, follow_up: str, evidence: str, categories: str
) -> None:
    """K4–K8: контакты, деньги, суд, семья, здоровье, Ally — заметки нет, ни целиком, ни частью."""
    verdict = _decide(Candidate(TOPIC, text, follow_up, evidence), said)
    assert isinstance(verdict, Rejection) and verdict.reason is Reason.NEVER_STORE
    assert verdict.category in {Category(name) for name in categories.split(",")}


# Одно поле заметки K2 испорчено — у отказа своя причина (иероглифы I3-H1 не режет);
# «kept» — красная сторона: «you're», «your» и точка в «St.» — годная форма, не отказ.
_REASONS = _table("""
text | You're having a discovery call with an agency on Friday. | kept
text | Your discovery call with an agency is on Friday. | kept
text | You have a discovery call with an agency from St. Petersburg on Friday! | kept
text | Ты созваниваешься с агентством в пятницу. | not_english
follow_up | 电话怎么样? | not_english
evidence | I have a call с агентством | not_english
text | Discovery call with an agency on Friday. | form
text | You call. | form
text | You have a call. It is on Friday. | form
text | You have a discovery call on Friday? | form
text | You have a discovery call and a call and a call and a call and a call and a call and a call and a call. | form
follow_up | Tell me how the discovery call went. | form
follow_up | So how how how how how how how how how how how how how how how? | form
follow_up | Would you rate your English out of ten? | contract
evidence | an agency on Monday | not_said
evidence | on Friday | not_said
""")


@pytest.mark.parametrize(("field", "value", "reason"), _REASONS)
def test_each_rule_names_its_own_reason(field: str, value: str, reason: str) -> None:
    """K10: отброшенный кандидат несёт свою причину — та и идёт в лог числом."""
    kept = replace(CALL_KEPT, **{field: value})
    expected = kept if reason == "kept" else Rejection(Reason(reason))
    assert _decide(replace(CALL, **{field: value}), CALL_SAID) == expected


def test_five_candidates_keep_only_the_good_in_model_order() -> None:
    """K10: из пяти — по-русски, не на «you», вопрос без «?» и два годных; сохранены годные."""
    raw = _raw(
        Candidate(TOPIC, "Ты читаешь Дюну.", "Как тебе книга?", "I started reading Dune"),
        CALL,
        Candidate(TOPIC, "Dune is the book you can't put down.", "Why?", "I can't put it down"),
        Candidate(TOPIC, "You can't put Dune down.", "Tell me more.", "I can't put it down"),
        DUNE,
    )
    result = _sift(raw, CALL_SAID, DUNE_SAID)
    assert isinstance(result, Sifted) and [m.text for m in result.kept] == [CALL.text, DUNE.text]
    assert [r.reason for r in result.rejected] == [Reason.NOT_ENGLISH, Reason.FORM, Reason.FORM]


def test_rejected_reach_the_log_as_reason_and_count_without_text(
    caplog: pytest.LogCaptureFixture, canary_text: str
) -> None:
    """K10: в логе причина, категория и число; текст с меткой стража канона — нигде."""
    mark = canary_text.split(maxsplit=1)[0]
    raw = _raw(
        Candidate(
            TOPIC, f"You owe {mark} fifty dollars.", "Did you pay?", f"I owe {mark} fifty dollars"
        ),
        Candidate(TOPIC, f"You started reading {mark}.", "How is it?", f"I started reading {mark}"),
        Candidate(TOPIC, f"Ты читаешь {mark}.", "Как книга?", f"I started reading {mark}"),
    )
    caplog.set_level(logging.INFO, logger="app.memory.guard")
    result = _sift(raw, f"I owe {mark} fifty dollars", f"I started reading {mark} last week")
    assert isinstance(result, Sifted) and [m.text for m in result.kept] == [
        f"You started reading {mark}."
    ]
    records = [r for r in caplog.records if r.name == "app.memory.guard"]
    logged = {(r.reason, r.category, r.count) for r in records}
    assert logged == {("never_store", Category.MONEY, 1), ("not_english", None, 1)}
    assert all(mark not in r.getMessage() for r in records)


@pytest.mark.parametrize(
    ("saved", "new"),
    [
        ("You started reading Dune.", "You're reading Dune."),
        ("You're reading Dune.", "You started reading Dune."),
        # от меньшего набора: короткий пересказ длинной заметки — тоже повтор, и наоборот
        ("You started reading Dune by Frank Herbert last week.", "You're reading Dune."),
        ("You're reading Dune.", "You started reading Dune by Frank Herbert last week."),
    ],
)
def test_same_thing_again_is_not_a_second_note(saved: str, new: str) -> None:
    """K12: «You're reading Dune.» рядом с «You started reading Dune.» — второй заметки нет."""
    candidate = replace(DUNE, text=new)
    assert _decide(candidate, DUNE_SAID, known=(saved,)) == Rejection(Reason.REPEAT)
    assert isinstance(_decide(candidate, DUNE_SAID, known=("You're learning to surf.",)), Candidate)


def test_neighbour_in_the_same_answer_is_a_repeat_too() -> None:
    """K12: две заметки об одном в одном ответе — сохраняется первая."""
    result = _sift(_raw(DUNE, replace(DUNE, text="You're reading Dune.")), DUNE_SAID)
    assert isinstance(result, Sifted) and [m.text for m in result.kept] == [DUNE.text]
    assert result.rejected == [Rejection(Reason.REPEAT)]


@pytest.mark.parametrize(
    "raw",
    [
        "Sure! Here is what I remember: you have a call on Friday.",
        json.dumps([asdict(CALL)]),
        json.dumps({"memories": "You have a call."}),
        json.dumps({"notes": []}),  # чужой ключ: заметки D3a.2 — не память
    ],
)
def test_answer_of_the_wrong_shape_is_rejected_whole(raw: str) -> None:
    """K11, часть guard: не та форма — отказ всего ответа; повтор и `failed` — memory-write."""
    assert _sift(raw, CALL_SAID) == Rejection(Reason.MALFORMED)


def test_broken_candidate_is_dropped_and_the_rest_still_count() -> None:
    """K10: кривой кандидат — отказ только ему (M-H1), годный рядом сохраняется."""
    good = asdict(CALL)
    broken = [{**good, "kind": "goal"}, {**good, "kind": ["plan"]}, {**good, "evidence": " "}]
    items = [*broken, {**good, "text": 42}, "You have a discovery call.", good]
    result = _sift(json.dumps({"memories": items}), CALL_SAID)
    assert isinstance(result, Sifted) and [m.text for m in result.kept] == [CALL.text]
    assert [r.reason for r in result.rejected] == [Reason.MALFORMED] * 5


def test_contract_numbers_are_the_signed_ones() -> None:
    """K10, K12: числа контракта — из подписанной спеки, список закрывает все шесть категорий."""
    assert (RULES.max_memories, RULES.min_quote_words, RULES.text_words) == (3, 3, (3, 25))
    assert (RULES.follow_up_max_words, RULES.repeat_share) == (15, 0.6)
    assert {category for category, _ in RULES.never_store.patterns} == set(Category)


@pytest.mark.parametrize("line", ["secrets: password", "money:", "money: (unclosed", "no colon"])
def test_never_store_line_that_cannot_be_read_fails_loudly(tmp_path: Path, line: str) -> None:
    """K4–K8: неизвестная категория, пустой (совпал бы со всем) или сломанный шаблон — ошибка."""
    path = tmp_path / "never.txt"
    path.write_text(f"{(CONTRACTS / 'memory_never_store.txt').read_text('utf-8')}{line}\n", "utf-8")
    with pytest.raises(ContractError, match=r"never\.txt"):
        load_never_store(path)


def test_category_or_number_left_out_fails_loudly(tmp_path: Path) -> None:
    """K8, K10: удалённый раздел списка или число контракта не подменяются молчанием."""
    source = (CONTRACTS / "memory_never_store.txt").read_text("utf-8").splitlines()
    never = "\n".join(line for line in source if not line.startswith("ally:"))
    (tmp_path / "memory_never_store.txt").write_text(never, "utf-8")
    contract = (CONTRACTS / "memory.contract.yaml").read_text("utf-8")
    for broken, named in ((contract, "ally"), (contract.replace("max_candidates: 3", ""), "max_")):
        (tmp_path / "memory.contract.yaml").write_text(broken, "utf-8")
        with pytest.raises(ContractError, match=named):
            load_rules(tmp_path)


# --- инварианты на переборе (§6.5 без зависимости — решение человека 2026-08-12) ---
# Ожидаемого значения нет — есть отношение, которое обязано держаться на любом входе.
# Слова начинаются с «zq»: такого нет ни среди служебных слов, ни в списке «никогда».

_SEPARATORS = (" ", ", ", ". ", "! ", " — ", "? ")
#: По реплике спеки на категорию — из таблицы K4–K8, где категория одна.
_TAINTS = [
    (Category(c), said) for c, said in {r[4]: r[0] for r in _NEVER_STORE if "," not in r[4]}.items()
]


def _word(rng: random.Random) -> str:
    return "zq" + "".join(rng.choices(string.ascii_lowercase, k=rng.randint(1, 6)))


def _samples(count: int = 300) -> list[tuple[list[str], int, list[str]]]:
    """Его реплики (1–4), номер одной из них и кусок её слов подряд (3–12)."""
    rng = random.Random(20261025)
    samples = []
    for _ in range(count):
        turns = [[_word(rng) for _ in range(rng.randint(3, 20))] for _ in range(rng.randint(1, 4))]
        index = rng.randrange(len(turns))
        start = rng.randrange(len(turns[index]) - 2)
        end = rng.randint(start + 3, min(len(turns[index]), start + 12))
        said = [t[0] + "".join(rng.choice(_SEPARATORS) + w for w in t[1:]) for t in turns]
        samples.append((said, index, turns[index][start:end]))
    return samples


def _quoting(fragment: list[str], index: int) -> Candidate:
    quoted = " ".join(w.upper() if index % 2 else w for w in fragment)
    return Candidate(TOPIC, "You " + " ".join(fragment) + ".", "How did it go?", quoted)


def test_kept_quote_is_always_a_verbatim_slice_of_one_of_his_turns() -> None:
    """K3 (инвариант): как бы модель ни процитировала, в заметку идёт кусок его реплики КАК ЕСТЬ."""
    for index, (said, _, fragment) in enumerate(_samples()):
        kept = _decide(_quoting(fragment, index), *said)
        assert isinstance(kept, Candidate), (said, fragment)
        assert any(kept.evidence in turn for turn in said)
        assert words(kept.evidence) == fragment
        unsaid = _quoting([*fragment, "xylophonezz"], index)  # слово, которого он не говорил
        assert _decide(unsaid, *said) == Rejection(Reason.NOT_SAID)


def test_category_anywhere_in_the_quoted_turn_always_drops_the_note() -> None:
    """K4–K8 (инвариант): категория в реплике с цитатой — отказ с ЭТОЙ категорией, где бы она ни стояла."""
    for index, (said, turn, fragment) in enumerate(_samples()):
        category, phrase = _TAINTS[index % len(_TAINTS)]
        tainted = [*said]
        tainted[turn] = f"{phrase}, {said[turn]}" if index % 2 else f"{said[turn]} and {phrase}"
        assert _decide(_quoting(fragment, index), *tainted) == Rejection(
            Reason.NEVER_STORE, category
        )


def test_repeat_is_symmetric_and_a_retelling_is_always_a_repeat() -> None:
    """K12 (инвариант): «повтор» не зависит от того, что пришло первым, а часть заметки — повтор её."""
    rng = random.Random(20261025)
    vocab = [f"zq{letter}" for letter in "abcdefghij"]
    for _ in range(300):
        mine, theirs = rng.sample(vocab, rng.randint(1, 8)), rng.sample(vocab, rng.randint(1, 8))
        a, b = "You " + " ".join(mine), "You " + " ".join(theirs)
        assert is_repeat(a, b, RULES.repeat_share) == is_repeat(b, a, RULES.repeat_share)
        part = "You " + " ".join(mine[: rng.randint(1, len(mine))])
        assert is_repeat(part, a, RULES.repeat_share) and is_repeat(a, part, RULES.repeat_share)


def test_kept_are_always_the_first_good_ones_in_model_order() -> None:
    """K10 (инвариант): сохранено не больше трёх, и это первые годные в порядке модели."""
    rng = random.Random(20261025)
    for _ in range(200):
        good = [rng.random() < 0.6 for _ in range(rng.randint(0, 7))]
        topics = [[f"zq{letter}{number}x" for letter in "abc"] for number in range(len(good))]
        candidates = [
            Candidate(TOPIC, ("You " if ok else "They ") + " ".join(t) + ".", "Why?", " ".join(t))
            for t, ok in zip(topics, good, strict=True)
        ]
        result = _sift(_raw(*candidates), *("I " + " ".join(t) for t in topics))
        assert isinstance(result, Sifted)
        expected = [c.text for c, ok in zip(candidates, good, strict=True) if ok][:3]
        assert [m.text for m in result.kept] == expected
        assert result.rejected.count(Rejection(Reason.OVER_LIMIT)) == max(0, sum(good) - 3)
