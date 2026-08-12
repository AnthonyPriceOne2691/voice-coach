"""Дыхание в живой WS-реплике: где пауза есть и где её быть не должно (E2, E4, E5)."""

import base64
from pathlib import Path
from typing import Any

import pytest
from starlette.testclient import TestClient

from app.main import create_app
from tests.fakes import FakeLlm, FakeStt, FakeTts, fake_tts_duration_s, wav_duration_s
from tests.helpers import (
    collect_until,
    drain_intro,
    drain_until_listening,
    make_container,
    send_utterance,
)

PAUSE_S = 0.35
LONG_ANSWER = "I built an internal CRM tool with separate queues and cut the team from 5 to 1"


def _chunk_durations(messages: list[dict[str, Any]]) -> list[float]:
    return [
        wav_duration_s(base64.b64decode(m["payload"]["chunk_base64"]))
        for m in messages
        if m["type"] == "audio" and m["payload"]["chunk_base64"]
    ]


def test_breath_between_sentences_but_not_before_the_first(tmp_path: Path) -> None:
    """E2 + E5: пауза звучит МЕЖДУ предложениями, перед первым её нет."""
    llm = FakeLlm(["Got it. ", "Why separate queues? "])
    container = make_container(tmp_path, llm, FakeStt(LONG_ANSWER))
    tts = container.tts
    assert isinstance(tts, FakeTts)

    with TestClient(create_app(container)) as client, client.websocket_connect("/ws/session") as ws:
        ws.send_json({"type": "start_interview", "payload": {}})
        drain_intro(ws)
        before = len(tts.synthesized)
        send_utterance(ws)
        turn = drain_until_listening(ws)

    spoken = tts.synthesized[before:]
    assert spoken == ["Got it.", "Why separate queues?"]  # два предложения хода
    raw = [fake_tts_duration_s(text) for text in spoken]
    sent = _chunk_durations(turn)

    assert len(sent) == 2
    assert sent[0] == pytest.approx(raw[0], abs=0.001)  # E5: первому дыхание не нужно
    assert sent[1] == pytest.approx(raw[1] + PAUSE_S, abs=0.001)  # E2: второму — нужно


def test_intro_has_no_leading_pause_and_turn_end_has_no_trailing_one(tmp_path: Path) -> None:
    """E4 + E5: интро начинается сразу, а после последнего слова тишины нет."""
    container = make_container(tmp_path, FakeLlm(["Ok. "]), FakeStt(LONG_ANSWER))
    tts = container.tts
    assert isinstance(tts, FakeTts)

    with TestClient(create_app(container)) as client, client.websocket_connect("/ws/session") as ws:
        ws.send_json({"type": "start_interview", "payload": {}})
        started = ws.receive_json()
        assert started["type"] == "session_started"
        intro_messages = drain_until_listening(ws)

    intro_chunks = _chunk_durations(intro_messages)
    assert intro_chunks[0] == pytest.approx(fake_tts_duration_s(tts.synthesized[0]), abs=0.001)

    # E4: завершающее сообщение хода — пустой чанк, паузу к нему не подмешивают
    finals = [
        m
        for m in intro_messages
        if m["type"] == "audio" and m["payload"]["final"] and not m["payload"]["chunk_base64"]
    ]
    assert len(finals) == 1


def test_pause_counter_resets_between_turns(tmp_path: Path) -> None:
    """Сброс на final — то, на чём держится корректность.

    Без него пауза уехала бы в НАЧАЛО следующей реплики, то есть в задержку
    перед первым словом Генри на каждом ходе после первого.
    """
    # с вопросом в конце: иначе енфорсер допишет seed третьим чанком и тест
    # начнёт мерить не то, что проверяет
    llm = FakeLlm(["First sentence here. ", "Why did you pick that? "])
    container = make_container(tmp_path, llm, FakeStt(LONG_ANSWER))
    tts = container.tts
    assert isinstance(tts, FakeTts)

    with TestClient(create_app(container)) as client, client.websocket_connect("/ws/session") as ws:
        ws.send_json({"type": "start_interview", "payload": {}})
        drain_intro(ws)
        send_utterance(ws)
        first_turn = drain_until_listening(ws)
        send_utterance(ws)
        second_turn = drain_until_listening(ws)
        ws.send_json({"type": "end_session", "payload": {"reason": "user"}})
        collect_until(ws, "session_ended")

    raw = [fake_tts_duration_s(t) for t in ("First sentence here.", "Why did you pick that?")]
    for turn in (first_turn, second_turn):
        chunks = _chunk_durations(turn)
        assert len(chunks) == 2
        # в КАЖДОМ ходе первый чанк без паузы, второй — с ней
        assert chunks[0] == pytest.approx(raw[0], abs=0.001)
        assert chunks[1] == pytest.approx(raw[1] + PAUSE_S, abs=0.001)
