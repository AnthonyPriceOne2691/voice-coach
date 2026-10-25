"""Подсказка вслух после ответа по сути через WS (D3a.2, talk-tips): C14–C17.

Модель, голос и распознавание — фейки; оркестратор, контракт, поток и база — настоящие.
Окно после конца ответа сужено до нуля: срок «конец звука + 1.5 s» судят модульные тесты
`test_talk_tips.py`, а здесь — что ход ждёт проверку, пока звучит ответ, и не дольше.
Ответы короткие намеренно: эти тесты гоняются за каждого мутанта `ws_voice.py`.
"""

import json
from pathlib import Path
from typing import Any, cast

import pytest
from starlette.testclient import TestClient

from app.main import create_app
from app.voice import talk_tips
from tests.fakes import FakeStt, FakeTts, RoutingLlm
from tests.helpers import (
    collect_until,
    drain_until_listening,
    fetch_talk,
    make_container,
    send_utterance,
)

SAID = "Yesterday I go to the office and meet my client."
NOTE = json.dumps(
    {
        "kind": "error",
        "said": "I go to the office and meet my client",
        "better": "I went to the office and met my client",
        "why": "past tense",
    }
)
NONE = json.dumps({"kind": "none", "said": "", "better": "", "why": ""})
TIP = "By the way, you could say: I went to the office and met my client — past tense."
REPLY = ["Nice, and then? "]  # одно предложение — 0.1 s звука у фейкового голоса


@pytest.fixture(autouse=True)
def _tip_window_ends_with_the_reply(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(talk_tips, "TIP_GRACE_S", 0.0)


def _talk(tmp_path: Path, llm: RoutingLlm, said: list[str]) -> tuple[list[Any], Any, FakeTts]:
    """Разговор: реплики по очереди, потом End; кадры каждого хода, запись и голос."""
    stt = FakeStt()
    container = make_container(tmp_path, llm, stt)
    turns = []
    with TestClient(create_app(container)) as client, client.websocket_connect("/ws/session") as ws:
        ws.send_json({"type": "start_talk", "payload": {}})
        started = ws.receive_json()
        drain_until_listening(ws)
        for text in said:
            stt.text = text
            send_utterance(ws)
            turns.append(drain_until_listening(ws))
        ws.send_json({"type": "end_session", "payload": {"reason": "user"}})
        collect_until(ws, "session_ended")
    talk = fetch_talk(container.settings.database_url, started["payload"]["session_id"])
    return turns, talk, cast(FakeTts, container.tts)


def _henry(frames: list[dict[str, Any]]) -> list[str]:
    return [
        str(m["payload"]["text"])
        for m in frames
        if m["type"] == "transcript" and m["payload"]["role"] == "agent"
    ]


def test_note_is_spoken_after_the_reply_and_never_reaches_the_model(tmp_path: Path) -> None:
    """C14: после ответа по сути — одна подсказка по шаблону, в транскрипте и в списке.

    Модель её не видит ни в ответе, ни в проверке, а Генри после отказа возвращается к
    своему вопросу, а не к подсказке.
    """
    llm = RoutingLlm(REPLY, [NOTE])
    turns, talk, tts = _talk(tmp_path, llm, [SAID, "Rate my English, please.", "It went well."])

    assert _henry(turns[0]) == ["Nice, and then?", TIP]
    assert [m["payload"]["final"] for m in turns[0] if m["type"] == "audio"] == [
        False,
        False,
        True,
    ]
    assert tts.synthesized.count(TIP) == 1  # в третьем ходе поправлять нечего
    assert _henry(turns[1])[0].endswith(" Nice, and then?")
    transcript = json.loads(talk.transcript_json)
    assert [(t["role"], t["state"]) for t in transcript[2:4]] == [
        ("agent", "CHAT"),
        ("agent", "TIP"),
    ]
    assert [n["spoken"] for n in json.loads(talk.metadata_json)["language_notes"]] == [True]
    seen = [m["content"] for messages, _ in llm.calls for m in messages]
    assert seen and not [content for content in seen if "By the way" in content]


def test_correction_by_the_model_is_cut_and_without_a_note_no_tip(tmp_path: Path) -> None:
    """C16: поправку модели енфорсер режет до озвучки; C15: нет заметки — только ответ."""
    reply = ["Sounds fun! ", "You could also say “I went to the gym”. ", "What did you do? "]
    turns, talk, tts = _talk(tmp_path, RoutingLlm(reply, [NONE]), ["Yesterday I go to the gym."])

    assert _henry(turns[0]) == ["Sounds fun!"]
    assert not [line for line in tts.synthesized if "could also say" in line]
    assert not [line for line in tts.synthesized if "By the way" in line]  # C15
    assert json.loads(talk.metadata_json)["hard_violations"] == 1


def test_the_mic_waits_for_a_check_that_ends_while_the_reply_plays(tmp_path: Path) -> None:
    """C17: проверка кончилась, пока звучит ответ (0.65 s), — подсказка ещё успевает."""
    reply = ["Oh, a client day! ", "How did the meeting go? "]
    turns, _, _ = _talk(tmp_path, RoutingLlm(reply, [NOTE], check_delay_s=0.05), [SAID])
    assert _henry(turns[0])[-1] == TIP


def test_a_check_late_for_the_end_of_the_reply_gives_no_tip(tmp_path: Path) -> None:
    """C17: проверка не успела к концу ответа — подсказки нет, микрофон открывается."""
    turns, talk, _ = _talk(tmp_path, RoutingLlm(REPLY, [None]), [SAID])
    assert _henry(turns[0]) == ["Nice, and then?"]
    assert turns[0][-1]["payload"]["value"] == "listening"
    metadata = json.loads(talk.metadata_json)
    assert (metadata["language_notes"], metadata["checks_cancelled"]) == ([], 1)
