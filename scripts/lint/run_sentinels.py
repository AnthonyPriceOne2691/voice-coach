"""Стражи исполнения: что тест прогнал через код, судится по факту (CQG §2.7c).

pytest-плагин контура, держит три строки §2: текст пользователя не уходит в лог
(судится СОДЕРЖАНИЕ, форму судит `unstructured-log`), значения секретов не уходят в
лог и в вывод, соединение, взятое кодом под тестом, возвращается в пул к концу теста.
Подключение — фрагмент `[tool.pytest.ini_options]` (Приложение B). Под mutmut стражи
молчат: их находка убивала бы мутанта вместо теста (§3.7). Перехватчики — в части
`sentinels_taps.py`.
"""

from __future__ import annotations

import os
import secrets

import pytest

from sentinels_taps import (
    MIN_SECRET,
    WATCH,
    watch_pool,
    watch_secrets,
    wrap_httpx,
    wrap_logging,
    wrap_websocket,
)

TOKEN = "cnry" + secrets.token_hex(5)


def record_text(entry) -> str:
    """Всё, что вызов способен вынести наружу: текст, аргументы, extra, исключение."""
    _who, _method, args, extra, exc = entry
    parts = [str(a) for a in args]
    if isinstance(extra, dict):
        parts += [str(v) for v in extra.values()]
    if exc is not None:
        parts.append(str(exc))
    return "\n".join(parts)


def excerpt(entry) -> str:
    """Строка записи для отчёта — с ЗАМАСКИРОВАННЫМИ секретами: отчёт уходит в лог CI,
    и показать в нём значение значило бы совершить ту самую утечку."""
    _who, method, args, _extra, _exc = entry
    msg, rest = (args[1], args[2:]) if method == "log" and len(args) > 1 else (args[0], args[1:])
    try:
        text = str(msg) % rest if rest else str(msg)
    except (TypeError, ValueError):
        text = str(msg)
    return mask(text)[:120]


def mask(text: str) -> str:
    """Значения секретов → `‹секрет ИМЯ›`. Отчёт уходит в лог CI, а у упавшего теста
    pytest печатает ещё и свой «Captured log» — сырым (замер на полигоне)."""
    for value, src in WATCH.marks.items():
        if src.startswith("секрет"):
            text = text.replace(value, f"‹{src}›")
    return text


def pytest_configure(config) -> None:
    # Метка регистрируется ВСЕГДА: под mutmut незнакомая метка — предупреждение, а
    # с `filterwarnings = ["error"]` из фрагмента — упавший сбор (замер на стенде).
    config.addinivalue_line("markers", "contour_allow_text(reason): текст в логе по "
                            "требованию (аудит) — причина обязательна, §2.7")
    if "MUTANT_UNDER_TEST" in os.environ:
        return                  # mutmut: находка стража убила бы мутанта вместо теста
    wrap_logging()
    wrap_httpx()
    watch_pool()
    config.pluginmanager.register(Sentinels(), "contour-sentinels")


class Sentinels:
    """Хуки на фазы теста: кто сейчас исполняется и что он оставил."""

    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_protocol(self, item):
        WATCH.nodeid = item.nodeid
        wrap_websocket()            # тест-клиент к этому моменту загружен проектом
        yield
        WATCH.nodeid = ""

    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_call(self, item):
        WATCH.phase = "call"
        yield
        WATCH.phase = ""

    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_makereport(self, item, call):
        outcome = yield
        rep = outcome.get_result()
        found = self.leaks(item, call.when, rep)
        rep.sections = [(title, mask(text)) for title, text in rep.sections]
        if found:
            WATCH.leaks += found
            rep.outcome = "failed"
            rep.longrepr = "стражи исполнения (§2.7, §2 пул):\n  " + "\n  ".join(found)

    def leaks(self, item, when: str, rep) -> list[str]:
        """Что фаза оставила: текст и секреты в логе и выводе, соединения вне пула."""
        watch_secrets()             # фикстура и monkeypatch ставят секрет уже ВНУТРИ теста
        records, WATCH.records = WATCH.records, []
        WATCH.seen += len(records)
        allow = item.get_closest_marker("contour_allow_text") is not None
        out = [f"лог {entry[0]}.{entry[1]} несёт {src}: {excerpt(entry)!r}"
               for entry in records for src in self.sources(entry, allow)]
        out += [f"вывод теста несёт {src}" for stream in (rep.capstdout, rep.capstderr)
                for src in WATCH.found(stream) if src.startswith("секрет")]
        return out + (self.lost_connections(item) if when == "teardown" else [])

    @staticmethod
    def sources(entry, allow: bool) -> list[str]:
        """Метки в записи. Строка клиента теста о СВОЁМ запросе — не утечка приложения."""
        if entry[0] == "httpx" and any(str(a) in WATCH.local_urls for a in entry[2]):
            return []
        return [src for src in WATCH.found(record_text(entry))
                if not allow or src.startswith("секрет")]

    @staticmethod
    def lost_connections(item) -> list[str]:
        lost = [k for k, v in WATCH.taken.items() if v == item.nodeid]
        for k in lost:
            del WATCH.taken[k]
        WATCH.lost += len(lost)
        return [f"{len(lost)} соединени(й) не вернулось в пул: взято кодом под тестом "
                "мимо контекст-менеджера"] if lost else []

    def pytest_terminal_summary(self, terminalreporter) -> None:
        names = sorted(s.split()[1] for s in WATCH.marks.values() if s.startswith("секрет"))
        texts = sum(1 for s in WATCH.marks.values() if not s.startswith("секрет"))
        tr = terminalreporter
        tr.write_line(
            f"стражи исполнения: записей прочитано {WATCH.seen} · секретов под меткой "
            f"{len(names)} ({', '.join(names) or '—'}) · текстов под меткой {texts} "
            f"(canary_text в {WATCH.text_tests} тест(ах)) · пул: взято {WATCH.pool}, "
            f"не вернулось {WATCH.lost} · утечек {len(WATCH.leaks)}")
        # «Ноль утечек» без меток — не чистота, а непросмотренное: печатается вслух.
        if not texts:
            tr.write_line("⚠ текст пользователя НЕ судился: ни один тест не отправил "
                          "свободный текст и не взял canary_text (§2.7)", yellow=True)
        if not names:
            tr.write_line("⚠ значения секретов НЕ судились: ни одной секретной "
                          f"переменной длиной от {MIN_SECRET} знаков (§2.7)", yellow=True)


@pytest.fixture
def canary_text() -> str:
    """Свободный текст с меткой: прогони его через свою точку входа."""
    WATCH.text_tests += 1
    value = f"{TOKEN} свободный текст пользователя"
    WATCH.mark(TOKEN, "canary_text")
    return value
