"""У каждого ключа контракта есть исполнитель — или запись «объявлено, не исполняется».

Класс L72 на контрактах (L73): `drift`, `logging` и `recovery.regenerate_prompt`
стояли в контрактах интервью и разбора с июля, а код их не читал — Phase 2 закрыта
2026-08-15, детектора дрейфа нет. Контракт, обещающий поведение без исполнителя,
врёт тому, кто его правит: замени `hard_violations_tighten: 3` на 2 — не изменится
ничего.

Тест — на перечень: обходит КАЖДЫЙ ключ каждого `data/contracts/*.contract.yaml` на
любой глубине, правило списка — по его `id`. Ключ исполняется, если его имя стоит
строковой константой в коде того, кто этот YAML читает; параметр голосового правила —
если его берут из `RuleSpec.params`; ключ, который загрузчик кладёт в одноимённое поле
своего типа (`ContractSpec`, `MemoryRules`), — если это поле читает кто-то вне
загрузчика. Иначе ключ стоит в `NOT_EXECUTED` своей семьи с причиной.

Чего тест НЕ доказывает: что исполнитель применяет значение верно, — это тесты
енфорсера, сводки и памяти. Он ловит «исполнителя нет вовсе». Докстринги и
комментарии чтением не считаются: константы берутся из AST.
"""

import ast
import dataclasses
from collections.abc import Iterable, Iterator, Mapping
from fnmatch import fnmatch
from pathlib import Path
from typing import Any

import pytest
import yaml

from app.config import REPO_ROOT
from app.contracts.spec import ContractSpec
from app.memory.rules import MemoryRules

CONTRACTS = REPO_ROOT / "data" / "contracts"
APP = REPO_ROOT / "backend" / "app"

#: Ключи правила, которые читает разбор списка, а не исполнитель проверки.
RULE_FRAME = {"id", "check"}


@dataclasses.dataclass(frozen=True)
class Family:
    """Контракты одного читателя: кто читает YAML и во что его кладёт."""

    files: tuple[str, ...]
    modules: tuple[str, ...]  # от backend/app; первый — загрузчик
    config: type
    params_via_rulespec: bool  # параметры правил — из `RuleSpec.params`
    not_executed: Mapping[str, str]


VOICE = Family(
    files=("interview.contract.yaml", "review.contract.yaml", "talk.contract.yaml"),
    modules=("contracts/spec.py", "contracts/enforcer.py"),
    config=ContractSpec,
    params_via_rulespec=True,
    # Шаблон пути ключа → почему не исполняется. Запись на раздел покрывает поддерево.
    not_executed={
        "version": "номер ревизии для человека (interview 2.0 — тренер вместо экзаменатора, "
        "2026-08-12): загрузчик его не читает, в метаданные сессии он не пишется",
        "mode": "загрузчик кладёт значение в `ContractSpec.mode`, а поле не читает никто: "
        "какой контракт у сессии, решает `container.py` по имени файла",
        "enforcement": "загрузчик кладёт значение в `ContractSpec.enforcement`, а поле не "
        "читает никто: енфорсер судит каждое предложение всегда (`TurnEnforcer.feed`)",
        "preconditions": "YAML не читается: P2-1 и P2-2 разбора исполняет `api/ws_voice.py` "
        "(`_on_start_review`: нет интервью или отвеченных вопросов — ошибка), тип сессии "
        "выбирает обработчик сообщения; `knowledge_profile_loaded` не исполняется — без "
        "файла профиля в промпт идёт заглушка, а сессия начинается",
        "recovery/regenerate_prompt": "подсказка перегенерации — константа `STRICT_REGENERATE` "
        "в `voice/turn_runner.py`, одна на все режимы (L73); файла `strict_regenerate` в "
        "`data/prompts/` нет",
        "recovery/fallback": "запасная реплика — `seed` плана оркестратора "
        "(`voice/turn_runner.py`); `templates/contract_fallback.txt`, на который указывал "
        "комментарий интервью, не читает никто",
        "drift": "детектора дрейфа нет (doc 13, «Drift detection»): пороги не считаются и ни "
        "на что не влияют; строить ли его — решение человека",
        "logging": "значения не читаются: счётчики `hard_violations`, `soft_violations`, "
        "`fallback_count` пишет в метаданные сессии `voice/session_flow.py` — до "
        "восстановления, как обещает `pre_recovery`; сами события нарушений не сохраняются",
        "*/recovery": "значение не читается: восстановление после нарушения — одна лестница "
        "на все правила в `voice/turn_runner.py` (перегенерация → обрезка → `seed`, у G1-H4 — "
        "дописанный `seed`); у декларативных I1-S2 и I1-S3 нарушения не возникает вовсе, а "
        "`regenerate_larger_budget` у I2-H5 (`num_predict` ×2) не исполняется — пустой поток "
        "перегенерируется с прежним бюджетом",
        "*/persona": "персона — в системном промпте режима; проверка `mode_persona` "
        "декларативная (`DECLARATIVE_CHECKS`), статус — advisory в `delivery/rule_enforcers.md`",
        "*/template": "I1-S3 декларативное: «Got it.» не дописывает никто, короткое "
        "подтверждение пропускает G1-H4 по `ack_whitelist.txt`",
        "invariants/hard/I2-H3_no_new_interview/scope": "сужения нет: енфорсер режет фразы "
        "`interview_forbidden.txt` в любом предложении разбора, а не только в вопросе без "
        "рамки разбора",
    },
)

MEMORY = Family(
    files=("memory.contract.yaml",),
    modules=("memory/rules.py",),
    config=MemoryRules,
    params_via_rulespec=False,
    not_executed={
        "mode": "метка для человека: загрузчик памяти берёт из контракта только числа правил "
        "и список «никогда»",
        "version": "номер ревизии для человека: загрузчик памяти его не читает",
        "enforcement": "`per_candidate` — описание: каждого кандидата судит `memory/guard.py`, "
        "значение не читается",
        "logging": "значение не читается: «только причина и число» исполняет `_log` в "
        "`memory/guard.py`",
        "*/check": "имя проверки — документация: правила памяти — код `memory/guard.py`, маркер "
        "каждого id держит `test_every_non_voice_invariant_leaves_a_mark_in_code`",
    },
)

FAMILIES = (VOICE, MEMORY)

#: Контракт, YAML которого не загружает никто: правила — код, связь держат другие сторожа.
MIRRORED: dict[str, str] = {
    "summary.contract.yaml": "YAML не загружает никто: правила S-H1…S-H6 — код "
    "`summary/validate.py` и `summary/service.py` (маркеры держит "
    "`test_every_non_voice_invariant_leaves_a_mark_in_code`), повтор с ошибкой валидатора и "
    "откат к минимальной сводке зашиты в `service.py`; `logging.sink: session_metadata` не "
    "исполняется — ошибки сводки идут в лог приложения",
}


# --- обход YAML -----------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class Key:
    path: str  # `recovery/max_retries`, `governance/hard/G1-H1_max_sentences/max`
    rule_param: bool  # параметр правила списка (не `id` и не `check`)

    @property
    def name(self) -> str:
        return self.path.rsplit("/", 1)[-1]


def _walk(node: Any, prefix: str = "", in_rule: bool = False) -> Iterator[Key]:
    if isinstance(node, dict):
        for key, value in node.items():
            path = f"{prefix}/{key}" if prefix else str(key)
            yield Key(path, in_rule and key not in RULE_FRAME)
            yield from _walk(value, path)
    elif isinstance(node, list):
        for index, item in enumerate(node):
            if isinstance(item, dict):
                yield from _walk(item, f"{prefix}/{item.get('id', index)}", in_rule=True)


def _keys(file: str) -> list[Key]:
    return list(_walk(yaml.safe_load((CONTRACTS / file).read_text(encoding="utf-8"))))


# --- что читает код ---------------------------------------------------------------


def _tree(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"))


def _docstrings(tree: ast.Module) -> set[int]:
    owners = (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
    return {
        id(node.body[0].value)
        for node in ast.walk(tree)
        if isinstance(node, owners)
        and node.body
        and isinstance(node.body[0], ast.Expr)
        and isinstance(node.body[0].value, ast.Constant)
    }


def _is_params(node: ast.AST) -> bool:
    return isinstance(node, ast.Attribute) and node.attr == "params"


def _params_key(node: ast.AST) -> str | None:
    """`rule.params["max"]` и `rule.params.get("states", …)` → `max`, `states`."""
    key: ast.AST | None = None
    if isinstance(node, ast.Subscript) and _is_params(node.value):
        key = node.slice
    elif (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "get"
        and _is_params(node.func.value)
        and node.args
    ):
        key = node.args[0]
    if isinstance(key, ast.Constant) and isinstance(key.value, str):
        return key.value
    return None


def _constants(modules: Iterable[str]) -> tuple[set[str], set[str]]:
    """(строковые константы кода без докстрингов, ключи из `RuleSpec.params`)."""
    names: set[str] = set()
    params: set[str] = set()
    for rel in modules:
        tree = _tree(APP / rel)
        docs = _docstrings(tree)
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Constant)
                and isinstance(node.value, str)
                and id(node) not in docs
            ):
                names.add(node.value)
            if (key := _params_key(node)) is not None:
                params.add(key)
    return names, params


@dataclasses.dataclass(frozen=True)
class Code:
    """Что читает код семьи: имена, параметры правил, поля типа загрузчика вне него."""

    names: frozenset[str]
    params: frozenset[str]
    fields: frozenset[str]  # все поля типа загрузчика
    fields_read: frozenset[str]  # те из них, что читает кто-то вне загрузчика


def _code(family: Family) -> Code:
    names, params = _constants(family.modules)
    loader = APP / family.modules[0]
    attributes = {
        node.attr
        for path in APP.rglob("*.py")
        if path != loader
        for node in ast.walk(_tree(path))
        if isinstance(node, ast.Attribute)
    }
    fields = frozenset(f.name for f in dataclasses.fields(family.config))
    return Code(frozenset(names), frozenset(params), fields, fields & attributes)


def _covers(pattern: str, path: str) -> bool:
    """Запись покрывает ключ, его поддерево или ключи по маске (`*/persona`)."""
    return path == pattern or path.startswith(f"{pattern}/") or fnmatch(path, pattern)


def _reason(family: Family, key: Key) -> str | None:
    return next((r for p, r in family.not_executed.items() if _covers(p, key.path)), None)


def _why_silent(family: Family, key: Key, code: Code) -> str | None:
    """`None` — исполняется; иначе — почему нет."""
    if key.rule_param and family.params_via_rulespec:
        if key.name not in code.params:
            return "параметр правила не читает никто из `RuleSpec.params`"
        return None
    if key.name not in code.names:
        return f"имени нет в коде читателя ({', '.join(family.modules)})"
    if key.name in code.fields and key.name not in code.fields_read:
        return (
            f"загрузчик кладёт ключ в `{family.config.__name__}.{key.name}`, а поле не читает никто"
        )
    return None


def _silent(family: Family, file: str, code: Code) -> list[str]:
    """Ключи без исполнителя и без записи. Под молчащим ключом вложенные не судятся:
    раздел, который не читают, не читают и целиком."""
    silent: list[str] = []
    dead: list[str] = []
    for key in _keys(file):
        if any(key.path.startswith(f"{d}/") for d in dead):
            continue
        if _reason(family, key) is not None:
            dead.append(key.path)
            continue
        if (why := _why_silent(family, key, code)) is not None:
            silent.append(f"{key.path} — {why}")
            dead.append(key.path)
    return silent


# --- сторожа ----------------------------------------------------------------------


def _family_of(file: str) -> Family:
    return next(family for family in FAMILIES if file in family.files)


@pytest.mark.parametrize("file", [f for family in FAMILIES for f in family.files])
def test_every_contract_key_is_executed_or_declared(file: str) -> None:
    family = _family_of(file)
    silent = _silent(family, file, _code(family))
    assert silent == [], (
        f"{file}: ключи без исполнителя — контракт обещает поведение, которого нет "
        f"(L72, L73). Подключи исполнителя или внеси ключ в NOT_EXECUTED с причиной: {silent}"
    )


def test_every_contract_file_is_read_or_mirrored() -> None:
    """Новый контракт приходит с читателем или с причиной, почему YAML не читает никто."""
    on_disk = {path.name for path in CONTRACTS.glob("*.contract.yaml")}
    declared = {f for family in FAMILIES for f in family.files} | set(MIRRORED)
    assert on_disk == declared, f"контракты вне сторожа: {sorted(on_disk ^ declared)}"
    loaded, _ = _constants(str(p.relative_to(APP)) for p in APP.rglob("*.py"))
    assert all(f in loaded for family in FAMILIES for f in family.files)
    stale = sorted(f for f in MIRRORED if f in loaded)
    assert stale == [], f"контракт объявлен незагружаемым, а код его грузит: {stale}"


def test_not_executed_entries_are_alive() -> None:
    """Запись на ключ, которого нет, или на ключ, который уже исполняют, — мёртвая.

    Судится сам ключ записи (`drift`, а не его поддерево; у маски — все совпавшие):
    начали читать `drift` — запись сужается до того, что по-прежнему молчит.
    """
    for family in FAMILIES:
        code = _code(family)
        keys = [key for file in family.files for key in _keys(file)]
        for pattern in family.not_executed:
            anchors = [
                k
                for k in keys
                if k.path == pattern or ("*" in pattern and _covers(pattern, k.path))
            ]
            assert anchors, f"NOT_EXECUTED[{pattern!r}] не совпал ни с одним ключом"
            executed = [k.path for k in anchors if _why_silent(family, k, code) is None]
            assert executed == [], f"NOT_EXECUTED[{pattern!r}] протух: {executed} исполняются"


def test_the_sweep_sees_the_contracts() -> None:
    """Сторож судит не пустоту (L92): обход видит ключи всех глубин, читатель — код."""
    interview = {key.path: key for key in _keys("interview.contract.yaml")}
    assert "drift/thresholds/hard_violations_tighten" in interview
    assert "recovery/max_retries" in interview
    assert interview["governance/hard/G1-H4_question_or_ack/states"].rule_param
    assert not interview["governance/hard/G1-H4_question_or_ack/check"].rule_param
    memory = {key.path for key in _keys("memory.contract.yaml")}
    assert "invariants/hard/M-H5_form/text_max_words" in memory
    voice, memory_code = _code(VOICE), _code(MEMORY)
    assert {"max_retries", "patterns_file"} <= voice.names
    assert {"max", "states", "ack_max_words", "patterns_file"} <= voice.params
    assert "max_retries" in voice.fields_read
    assert {"min_quote_words", "follow_up_max_words"} <= memory_code.fields_read
