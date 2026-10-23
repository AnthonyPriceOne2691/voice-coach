"""У каждого ключа настроек есть читатель вне экрана Settings (уроки L69, L71).

Порог тишины 49 дней и переключатель живого транскрипта полтора месяца
хранились, отдавались, валидировались и показывались на экране Settings — и не
меняли ничего: читателя у ключа не было. Сторож связки в
`useVoiceSession.test.tsx` стоял на один ключ и закрыл случай, а не класс.
Этот тест — на перечень: каждый ключ `DEFAULTS` обязан встречаться в коде,
который не является ни экраном Settings, ни объявлением, ни хранилищем, ни
маршрутом настроек.

Чего тест НЕ доказывает: что найденный читатель применяет значение правильно.
Он ловит «читателя нет вовсе» — ровно так выглядели оба дефекта. Упоминание
ключа в комментарии читателем не считается: комментарии вырезаются до поиска.
Вырезка грубая — срезает и `//` внутри строк, — но ключ после URL в той же
строке не стоит нигде.
"""

import re
from pathlib import Path

import pytest

from app.config import REPO_ROOT
from app.storage.repositories.settings_repo import DEFAULTS

# Код, который ключ хранит, объявляет, показывает или валидирует, но не
# применяет. Встреча ключа здесь читателем не считается.
NOT_READERS = {
    "frontend/src/pages/SettingsPage.tsx",  # экран Settings: показ и запись
    "frontend/src/components/MicrophoneSetting.tsx",  # часть экрана Settings
    "frontend/src/types/api.ts",  # объявление типа ответа
    "backend/app/storage/repositories/settings_repo.py",  # умолчания и хранение
    "backend/app/api/routes_settings.py",  # валидация PATCH /settings
}

# Ключ, который законно только показывается, — сюда, с причиной. Пусто: каждый
# ключ сегодня обещает менять поведение.
DISPLAY_ONLY: dict[str, str] = {}

SOURCES = (("frontend/src", ("*.ts", "*.tsx")), ("backend/app", ("*.py",)))
TS_COMMENTS = re.compile(r"/\*.*?\*/|//[^\n]*", re.DOTALL)
PY_COMMENTS = re.compile(r"#[^\n]*")


def _code(path: Path) -> str:
    """Текст файла без комментариев: упоминание в комментарии — не чтение."""
    comments = PY_COMMENTS if path.suffix == ".py" else TS_COMMENTS
    return comments.sub("", path.read_text(encoding="utf-8"))


def _readers(key: str) -> list[str]:
    found = []
    for root, patterns in SOURCES:
        for pattern in patterns:
            for path in (REPO_ROOT / root).rglob(pattern):
                rel = path.relative_to(REPO_ROOT).as_posix()
                if rel in NOT_READERS or ".test." in path.name:
                    continue
                if key in _code(path):
                    found.append(rel)
    return sorted(found)


@pytest.mark.parametrize("key", sorted(DEFAULTS))
def test_every_setting_has_a_reader(key: str) -> None:
    if key in DISPLAY_ONLY:
        pytest.skip(DISPLAY_ONLY[key])
    assert _readers(key), (
        f"ключ настроек {key!r} никто не читает вне экрана Settings, объявления, "
        "хранилища и маршрута: он хранится и показывается, но поведения не меняет "
        "(уроки L69, L71). Подключи читателя или внеси ключ в DISPLAY_ONLY с причиной"
    )


def test_not_readers_still_exist() -> None:
    """Список исключений не протух: переименование молча расширило бы поиск."""
    missing = sorted(p for p in NOT_READERS if not (REPO_ROOT / p).is_file())
    assert not missing, f"файлы из NOT_READERS исчезли: {missing}"


def test_display_only_names_real_keys() -> None:
    """Исключение для ключа, которого нет, — мёртвая запись, а не причина."""
    assert set(DISPLAY_ONLY) <= set(DEFAULTS)
