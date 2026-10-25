"""Проверка речи в разговоре через WS (D3a.2, talk-check): что записано и когда звалась модель.

Модель, голос и распознавание — фейки; оркестратор, контракт, поток и база — настоящие.
Заметка попадает в базу со следующим чекпойнтом, поэтому каждый тест кончает сессию
и читает её запись, а не память обработчика.
"""

import json
import math
from pathlib import Path
from typing import Any

import pytest
from starlette.testclient import TestClient

from app.main import create_app
from app.orchestrator.tips import CANDIDATE_SCHEMA
from app.voice import talk_tips
from tests.fakes import FakeStt, RoutingLlm
from tests.helpers import drain_until_listening, fetch_talk, make_container, send_utterance

REPLY = ["Oh, a client day! ", "How did the meeting go? "]
C2_SAID = "Yesterday I go to the office and meet my client."
C2_CHECK = json.dumps(
    {
        "kind": "error",
        "said": "I go to the office and meet my client",
        "better": "I went to the office and met my client",
        "why": "past tense",
    }
)
NONE_CHECK = json.dumps({"kind": "none", "said": "", "better": "", "why": ""})


@pytest.fixture(autouse=True)
def _tip_window_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    """Здесь судится проверка и её отмена, а не подсказка вслух (её — test_ws_talk_tips).

    С открытым окном ход с висящей проверкой ждал бы конец звука + 1.5 s, и каждый
    тест отмены платил бы эти секунды — в том числе за каждого мутанта `ws_voice.py`.
    """
    monkeypatch.setattr(talk_tips, "TIP_GRACE_S", -math.inf)


def _until_turn_end(ws: Any) -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = []
    while not messages or not (
        messages[-1]["type"] == "session_ended"
        or (messages[-1]["type"] == "state" and messages[-1]["payload"]["value"] == "listening")
    ):
        messages.append(ws.receive_json())
    return messages


def _converse(
    tmp_path: Path, llm: RoutingLlm, utterances: list[str], *, wait_checks: bool = True
) -> tuple[dict[str, Any], Any]:
    """Открыть разговор, сказать реплики по очереди, закрыть кнопкой; вернуть запись."""
    stt = FakeStt()
    container = make_container(tmp_path, llm, stt)
    with TestClient(create_app(container)) as client, client.websocket_connect("/ws/session") as ws:
        ws.send_json({"type": "start_talk", "payload": {}})
        started = ws.receive_json()
        drain_until_listening(ws)
        for said in utterances:
            llm.check_done.clear()
            stt.text = said
            send_utterance(ws)
            _until_turn_end(ws)
            if wait_checks and llm.check_calls:
                assert llm.check_done.wait(5)
        ws.send_json({"type": "end_session", "payload": {"reason": "user"}})
        _until_ended(ws)
    talk = fetch_talk(container.settings.database_url, started["payload"]["session_id"])
    assert talk is not None
    return json.loads(talk.metadata_json or "{}"), talk


def _until_ended(ws: Any) -> None:
    while ws.receive_json()["type"] != "session_ended":
        pass


def test_error_is_noted_after_the_reply_with_the_recognized_fragment(tmp_path: Path) -> None:
    """C2: ошибка в реплике — заметка с дословным фрагментом; реплику Генри это не трогает."""
    llm = RoutingLlm(REPLY, [C2_CHECK])
    metadata, talk = _converse(tmp_path, llm, [C2_SAID])
    notes = metadata["language_notes"]
    assert [(n["kind"], n["said"], n["better"], n["why"]) for n in notes] == [
        (
            "error",
            "I go to the office and meet my client",
            "I went to the office and met my client",
            "past tense",
        )
    ]
    transcript = json.loads(talk.transcript_json)
    assert transcript[notes[0]["turn_index"]]["text"] == C2_SAID
    assert (metadata["checks_run"], metadata["checks_noted"]) == (1, 1)


def test_check_runs_after_the_reply_on_the_same_conversation_prefix(tmp_path: Path) -> None:
    """C8: проверка — ПОСЛЕ ответа и на том же префиксе: история + ответ Генри + просьба."""
    llm = RoutingLlm(REPLY, [C2_CHECK])
    _converse(tmp_path, llm, [C2_SAID])
    schemas = [schema for _, schema in llm.calls]
    check_at = schemas.index(CANDIDATE_SCHEMA)
    reply_messages = llm.calls[check_at - 1][0]  # реплика Генри — вызов прямо перед проверкой
    assert llm.calls[check_at - 1][1] is None
    check = llm.check_calls[0]
    assert check[:-1] == [*reply_messages, {"role": "assistant", "content": "".join(REPLY).strip()}]
    assert C2_SAID in check[-1]["content"]


def test_clean_and_casual_speech_leave_no_note(tmp_path: Path) -> None:
    """C1, C4: модель ничего не нашла — заметок нет, проверка посчитана."""
    llm = RoutingLlm(REPLY, [NONE_CHECK])
    metadata, _ = _converse(
        tmp_path,
        llm,
        [
            "I went to the gym this morning and it was packed.",
            "Yeah, went there yesterday, was fun.",
        ],
    )
    assert metadata["language_notes"] == []
    assert (metadata["checks_run"], metadata["checks_noted"]) == (2, 0)


def test_fix_of_words_that_were_not_said_is_dropped(tmp_path: Path) -> None:
    """C6: кандидат про несказанные слова — код отбрасывает, заметки нет."""
    wrong = json.dumps(
        {"kind": "error", "said": "I goes to work", "better": "I go to work", "why": ""}
    )
    llm = RoutingLlm(REPLY, [wrong])
    metadata, _ = _converse(tmp_path, llm, [C2_SAID])
    assert metadata["language_notes"] == []


def test_same_mistake_twice_gives_one_note(tmp_path: Path) -> None:
    """C7: та же ошибка во втором ходе — второй заметки нет."""
    llm = RoutingLlm(REPLY, [C2_CHECK])
    metadata, _ = _converse(tmp_path, llm, [C2_SAID, C2_SAID])
    assert len(metadata["language_notes"]) == 1
    assert (metadata["checks_run"], metadata["checks_noted"]) == (2, 1)


def test_requests_answered_by_code_are_not_checked(tmp_path: Path) -> None:
    """Просьбы к Генри (тема, темп) — не речь для разбора: проверка не зовётся вовсе."""
    llm = RoutingLlm(REPLY, [C2_CHECK])
    metadata, _ = _converse(
        tmp_path, llm, ["Can we talk about something else?", "Could you speak slower?"]
    )
    assert llm.check_calls == []
    assert metadata["checks_run"] == 0


def test_next_utterance_cancels_an_unfinished_check(tmp_path: Path) -> None:
    """C8: Антон заговорил раньше, чем кончилась проверка, — она отменяется, ответ её не ждёт."""
    llm = RoutingLlm(REPLY, [None, NONE_CHECK])
    stt = FakeStt()
    container = make_container(tmp_path, llm, stt)
    with TestClient(create_app(container)) as client, client.websocket_connect("/ws/session") as ws:
        ws.send_json({"type": "start_talk", "payload": {}})
        started = ws.receive_json()
        drain_until_listening(ws)
        stt.text = C2_SAID
        send_utterance(ws)
        _until_turn_end(ws)  # проверка первой реплики висит
        stt.text = "It went well, they liked the demo."
        send_utterance(ws)
        second = _until_turn_end(ws)
        ws.send_json({"type": "end_session", "payload": {"reason": "user"}})
        _until_ended(ws)
    agent_lines = [
        m for m in second if m["type"] == "transcript" and m["payload"]["role"] == "agent"
    ]
    assert agent_lines, "второй ответ Генри не дошёл — он ждал висящую проверку"
    talk = fetch_talk(container.settings.database_url, started["payload"]["session_id"])
    assert talk is not None
    metadata = json.loads(talk.metadata_json or "{}")
    assert metadata["checks_cancelled"] == 1
    assert metadata["language_notes"] == []


def test_ending_the_talk_with_a_hanging_check_does_not_hang(tmp_path: Path) -> None:
    """C8: конец разговора снимает висящую проверку; сессия закрыта как completed."""
    llm = RoutingLlm(REPLY, [None])
    metadata, talk = _converse(tmp_path, llm, [C2_SAID], wait_checks=False)
    assert talk.status == "completed"
    assert metadata["checks_cancelled"] == 1


def test_disconnect_with_a_hanging_check_still_finishes_the_session(tmp_path: Path) -> None:
    """C8: клиент ушёл, проверка висит — уборка её снимает, транскрипт дописан."""
    llm = RoutingLlm(REPLY, [None])
    stt = FakeStt(C2_SAID)
    container = make_container(tmp_path, llm, stt)
    with TestClient(create_app(container)) as client:
        with client.websocket_connect("/ws/session") as ws:
            ws.send_json({"type": "start_talk", "payload": {}})
            started = ws.receive_json()
            drain_until_listening(ws)
            send_utterance(ws)
            _until_turn_end(ws)
    # Читать ПОСЛЕ гашения приложения: lifespan дожидается уборки отключённой сессии
    # (`live_ws_cleanups`), а до него запись может быть ещё не дописана.
    talk = fetch_talk(container.settings.database_url, started["payload"]["session_id"])
    assert talk is not None
    assert talk.ended_at is not None
    assert json.loads(talk.metadata_json or "{}")["checks_cancelled"] == 1
