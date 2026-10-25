"""Подсказка вслух (D3a.2, talk-tips): текст по шаблону кода, срок и конец звука — модульно.

Сквозь WS то же судит `test_ws_talk_tips.py`; здесь — то, что там видно только временем:
на какой срок подсказка ждёт проверку и как сервер считает конец звука у клиента.
"""

from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
import yaml

from app.config import REPO_ROOT
from app.contracts.enforcer import ContractEnforcer, TurnContext
from app.contracts.spec import load_contract
from app.orchestrator.talk import load_script
from app.voice.talk_tips import PlaybackClock, TalkTips, Tip, tip_line
from tests.fakes import FAKE_TTS_RATE, fake_wav

SCRIPT = REPO_ROOT / "data" / "talk" / "talk.yaml"
TEMPLATES = load_script(SCRIPT).tips
NO_CORRECTIONS = "I3-H4_no_corrections"
NOTE = {"better": "I went to the office and met my client.", "why": "past tense."}


def test_tip_is_the_code_template_with_the_better_phrase_and_the_reason() -> None:
    """C14: «By the way, you could say: … — past tense.»; без причины — без тире."""
    assert tip_line(NOTE, TEMPLATES) == (
        "By the way, you could say: I went to the office and met my client — past tense."
    )
    plain = {"better": "I bought an iPhone X", "why": ""}
    assert tip_line(plain, TEMPLATES) == "By the way, you could say: I bought an iPhone X."


@pytest.mark.parametrize(
    ("name", "template"),
    [("with_reason", "By the way, you could say: {better}."), ("without_reason", "By the way.")],
)
def test_script_without_a_complete_tip_template_does_not_load(
    tmp_path: Path, name: str, template: str
) -> None:
    """C14: подсказку говорит код — шаблон без своих полей заметки не грузится."""
    data = yaml.safe_load(SCRIPT.read_text(encoding="utf-8"))
    data["tips"][name] = template
    broken = tmp_path / "talk.yaml"
    broken.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    with pytest.raises(ValueError, match=f"tips.{name}"):
        load_script(broken)


def test_tip_template_is_plain_english_that_only_the_code_may_say() -> None:
    """C16: шаблон проходит контракт разговора, кроме правила о поправках, — а оно его ловит.

    Значит, сказать подсказку может только код: у модели её срежет енфорсер.
    """
    spec = load_contract(REPO_ROOT / "data" / "contracts" / "talk.contract.yaml")
    rest = [rule for rule in spec.rules if rule.rule_id != NO_CORRECTIONS]
    without, full = ContractEnforcer(replace(spec, rules=rest)), ContractEnforcer(spec)
    for template in TEMPLATES.values():
        line = template.format(better="I went to the office", why="past tense")
        assert without.start_turn(TurnContext(state="CHAT")).feed(line) is None
        caught = full.start_turn(TurnContext(state="CHAT")).feed(line)
        assert caught is not None and caught.rule_id == NO_CORRECTIONS


def test_playback_ends_where_the_client_queue_ends() -> None:
    """C17: конец звука — как у `AudioQueue`: встык за прежним, после паузы — от «сейчас».

    `final` закрывает реплику: следующая начинается от «сейчас», даже если по часам
    сервера прежняя ещё звучит (человек заговорил — значит, клиент её доиграл).
    """
    now = 0.0
    clock = PlaybackClock(lambda: now)
    clock.sent(fake_wav(FAKE_TTS_RATE // 10), final=False)  # 0.1 s
    clock.sent(fake_wav(FAKE_TTS_RATE // 5), final=False)  # 0.2 s, пока играет первый
    assert clock.ends_at == pytest.approx(0.3)
    clock.sent(b"", final=True)  # пустой `final` закрывает реплику
    clock.sent(fake_wav(FAKE_TTS_RATE // 10), final=False)
    assert clock.ends_at == pytest.approx(0.1)
    now = 20.0
    clock.sent(fake_wav(FAKE_TTS_RATE // 10), final=False)
    assert clock.ends_at == pytest.approx(20.1)


class _Checks:
    """Проверка, которая отвечает сразу и запоминает, до какого срока её ждали."""

    def __init__(self, note: dict[str, Any] | None) -> None:
        self.note = note
        self.deadlines: list[float] = []

    async def note_by(self, deadline: float) -> dict[str, Any] | None:
        self.deadlines.append(deadline)
        return self.note


async def test_tip_waits_for_the_check_until_the_reply_ends_plus_grace() -> None:
    """C17: проверку ждут до конца звука ответа + 1.5 s; с заметкой — подсказка, без — нет."""
    note = dict(NOTE)
    checks = _Checks(note)
    tips = TalkTips(checks, TEMPLATES)  # type: ignore[arg-type]
    assert await tips.after_reply(audio_ends_at=100.0) == Tip(tip_line(note, TEMPLATES), note)
    assert checks.deadlines == [101.5]
    checks.note = None
    assert await tips.after_reply(audio_ends_at=5.0) is None
