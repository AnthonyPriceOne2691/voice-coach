"""Текст пользователя под стражем исполнения (CQG §2.7c): метку несёт STT, а не запрос.

Страж `run_sentinels` метит свободный текст, который тест ОТПРАВИЛ в приложение:
тело HTTP-запроса и кадр WebSocket. У Генри текст пользователя рождается в
распознавании речи, а WS-кадр `utterance_end` несёт base64 аудио, — поэтому без
этого модуля итог прогона честно печатал «текст пользователя НЕ судился» (замер
23.10 на 272 тестах: текстов под меткой 0).

Метку здесь несёт фикстура `canary_text`: фейковый STT отдаёт её как распознанную
реплику, и она идёт настоящим путём — WS-вход, фильтр транскрипта, детекторы
мета-ходов, оркестратор, модель, запись. Вызов логгера с этим текстом страж роняет
вместе с тестом, на любом уровне: перехват стоит ДО проверки уровня, потому что
INFO, молчащий при нынешней настройке логов, заговорит при первой отладке.

Каждый тест сначала доказывает, что метка ДОШЛА до пути (модель её получила,
пришла ошибка STT_EMPTY): иначе зелёный цвет значил бы «текст не прошёл», а не
«текст не утёк».
"""

import json
import logging
from pathlib import Path
from typing import Any

import pytest
from starlette.testclient import TestClient

from app.main import create_app
from tests.fakes import FakeLlm, FakeStt, RoutingLlm
from tests.helpers import (
    collect_until,
    drain_intro,
    drain_until_listening,
    make_container,
    send_utterance,
)


@pytest.fixture(autouse=True)
def _aiosqlite_trace_is_not_our_sink(monkeypatch: pytest.MonkeyPatch) -> None:
    """След aiosqlite выключен из суда ПОИМЁННО — и только пока он не может прозвучать.

    ⚠ Это обход стража, а не его исполнение, и он назван (STACK-ACCEPTANCE,
    «Остатки обновления 2.74»). aiosqlite зовёт `LOG.debug("executing %s", function)`
    на КАЖДОМ запросе без проверки уровня, а `function` — partial с SQL и
    параметрами, то есть с транскриптом. Страж судит вызов до уровня и роняет
    любой тест, где реплика доходит до базы (замер 23.10: 8 записей `aiosqlite.debug`
    на двух тестах, наших строк — 0). Вызов не наш, поправить его проект не может;
    прозвучать он может только при DEBUG у логгера `aiosqlite` или у корня, а этого
    нет ни в тестах, ни под uvicorn (`dev.sh`: корень WARNING, замер 23.10). Поэтому
    глушится ровно он — и проверкой, а не верой: включит кто-то DEBUG — фикстура
    упадёт, и решение придётся принимать заново. Логгеры приложения судятся как прежде.
    """
    trace = logging.getLogger("aiosqlite")
    assert not trace.isEnabledFor(logging.DEBUG), "DEBUG у aiosqlite включён — его след уже сток"
    monkeypatch.setattr(trace, "debug", lambda *_args, **_kwargs: None)


def _mark(canary_text: str) -> str:
    """Слово-метка фикстуры: оно латиницей и переживает англоязычный фильтр транскрипта."""
    return canary_text.split(maxsplit=1)[0]


def _end(ws: Any) -> None:
    ws.send_json({"type": "end_session", "payload": {"reason": "user"}})
    collect_until(ws, "session_ended")


def _said(messages: list[dict[str, Any]]) -> list[str]:
    return [
        str(m["payload"]["text"])
        for m in messages
        if m["type"] == "transcript" and m["payload"]["role"] == "user"
    ]


@pytest.mark.parametrize("start", ["start_interview", "start_talk"])
def test_recognized_speech_reaches_the_model_but_not_the_log(
    tmp_path: Path, canary_text: str, start: str
) -> None:
    """Распознанная реплика — модели и в транскрипт; в лог — ни на каком уровне."""
    mark = _mark(canary_text)
    llm = FakeLlm(["Got it. ", "What happened next? "])
    container = make_container(tmp_path, llm, FakeStt(canary_text))
    with TestClient(create_app(container)) as client, client.websocket_connect("/ws/session") as ws:
        ws.send_json({"type": start, "payload": {}})
        drain_intro(ws)
        send_utterance(ws)
        turn = drain_until_listening(ws)
        _end(ws)

    assert any(mark in line for line in _said(turn))
    assert mark in json.dumps(llm.calls), "метка не дошла до модели — страж судил бы пустоту"


def test_rejected_utterance_keeps_its_raw_transcript_out_of_the_log(
    tmp_path: Path, canary_text: str
) -> None:
    """STT_EMPTY: сырой транскрипт человеку показывается, а в лог не пишется."""
    container = make_container(tmp_path, FakeLlm(["Ok. "]), FakeStt(canary_text))
    # Порог выше любого числа слов метки — реплика гарантированно отвергается,
    # какой бы текст фикстура ни несла и что бы ни оставил фильтр транскрипта.
    container.settings.min_transcript_words = len(canary_text.split()) + 1
    with TestClient(create_app(container)) as client, client.websocket_connect("/ws/session") as ws:
        ws.send_json({"type": "start_interview", "payload": {}})
        drain_intro(ws)
        send_utterance(ws)
        turn = drain_until_listening(ws)
        _end(ws)

    errors = [m["payload"] for m in turn if m["type"] == "error"]
    assert [e["code"] for e in errors] == ["STT_EMPTY"]
    assert _mark(canary_text) in errors[0]["message"]  # «heard: …» — человеку, не в лог


def test_tip_built_from_the_users_words_stays_out_of_the_log(
    tmp_path: Path, canary_text: str
) -> None:
    """C14: подсказка из слов Антона звучит и пишется в транскрипт, но в лог не уходит."""
    mark = _mark(canary_text)
    note = {"kind": "style", "said": mark, "better": f"the {mark}", "why": "more natural"}
    llm = RoutingLlm(["Nice! "], [json.dumps(note)])
    container = make_container(tmp_path, llm, FakeStt(canary_text))
    with TestClient(create_app(container)) as client, client.websocket_connect("/ws/session") as ws:
        ws.send_json({"type": "start_talk", "payload": {}})
        drain_intro(ws)
        send_utterance(ws)
        turn = drain_until_listening(ws)
        _end(ws)

    henry = [m["payload"]["text"] for m in turn if m["type"] == "transcript"]
    assert any(f"the {mark}" in line for line in henry), "метка не дошла до подсказки"
