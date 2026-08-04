#!/usr/bin/env python3
"""Self-test for the canon stack: every fenced code block must parse.

Usage:
  python stack_selftest.py [dir]

Проверяет:
  * python-блоки  -> ast.parse
  * bash-блоки    -> bash -n
  * yaml-блоки    -> yaml.safe_load (или запрет табов, если PyYAML нет)
  * сбалансированность ``` в каждом файле
  * версии в шапках канонов == таблица §1 в AGENT_STACK.md

Exit 0 = всё чисто. Exit 1 = хоть один блок не парсится / версии разошлись.
"""

from __future__ import annotations

import ast
import re
import subprocess
import sys
from pathlib import Path

CANONS = (
    "AGENT_STACK.md",
    "AGENT_DELIVERY_HARNESS.md",
    "CODE_QUALITY_GATES.md",
    "OKF_KNOWLEDGE_BUNDLE.md",
)
CHECKED_LANGS = {"python", "bash", "sh", "yaml", "yml"}


def blocks(text: str) -> tuple[list[tuple[int, str, str]], int]:
    """[(line_no, lang, code)] + число незакрытых фенсов.

    Две правки после приёмочного развёртывания — обе про то, что эта функция была
    ровно тем «инструментом проверки, который не видит своей области», против
    которого написан весь CQG §6:

    * **Отступ.** `line.startswith("```")` не видел фенсы с отступом, а их четыре:
      два в CQG (процедура §5 шаги 4–5) и два в OKF. То есть исполняемые блоки
      процедуры развёртывания не проверялись НИКОГДА. Теперь фенс ищется по
      `lstrip()`, а тело блока сохраняется как есть.
    * **Глубина.** Функция была ТУМБЛЕРОМ, хотя Delivery §7.2 велит извлекать
      «считая глубину, как `blocks()` в stack_selftest.py» — то есть канон указывал
      на контрпример. Измерено: на шаблоне A.1 тумблер даёт 46 строк и **теряет**
      блок `agent-permissions`, счёт глубины — 79 строк и сохраняет его. Ровно тот
      дефект, от которого §7.2 предупреждает своих читателей.

    Вложенное открытие — фенс с info-строкой; закрытие — голой. Незакрытый блок
    остаётся ошибкой: несбалансированность мы хотим видеть, а не угадывать.
    """
    out: list[tuple[int, str, str]] = []
    lang: str | None = None
    depth = 0
    start = 0
    buf: list[str] = []
    for i, raw in enumerate(text.splitlines(), 1):
        line = raw.lstrip()
        if not line.startswith("```"):
            if lang is not None:
                buf.append(raw)
            continue
        info = line[3:].strip().lower()
        if lang is None:                       # открытие верхнего уровня
            lang, start, buf, depth = info, i, [], 1
            continue
        if info:                               # вложенное открытие
            depth += 1
            buf.append(raw)
            continue
        depth -= 1                             # закрытие
        if depth == 0:
            out.append((start, lang, "\n".join(buf)))
            lang = None
        else:
            buf.append(raw)
    return out, (1 if lang is not None else 0)


try:
    import yaml  # type: ignore

    HAVE_YAML = True
except ImportError:  # pragma: no cover - зависит от машины
    HAVE_YAML = False

# Сколько yaml-блоков прошло УРЕЗАННУЮ проверку (без парсера). Считается, чтобы
# итоговая строка не могла прочитаться как «всё проверено».
yaml_unparsed = 0


def check_yaml(code: str) -> str | None:
    """None = чисто. Без PyYAML проверка УРЕЗАНА, и это обязано быть видно.

    Стоимость молчания измерена на живом прогоне: `entry:` pre-commit-хука получил
    в текст «Установка: pip install …», последовательность `": "` в plain-скаляре
    YAML запрещена, и не парсился ВЕСЬ конфиг — pre-commit не стартовал ни одним
    хуком. Самопроверка при этом печатала «0 failures», потому что PyYAML на машине
    не стоял и ветка молча деградировала до поиска табов. Дефект нашло приёмочное
    развёртывание, а не этот скрипт — то есть скрипт был именно тем «гейтом,
    который ничего не видит», против которого написан весь CQG §6.
    """
    global yaml_unparsed
    if not HAVE_YAML:
        yaml_unparsed += 1
        # Без парсера ловим самое частое: таб в отступе YAML запрещён спекой.
        for n, line in enumerate(code.splitlines(), 1):
            if line[:1] == "\t" or (line.strip() and "\t" in line[: len(line) - len(line.lstrip())]):
                return f"tab indentation at line {n} (YAML forbids tabs)"
        return None
    try:
        # safe_load_all, а не safe_load: блоки-шаблоны frontmatter обрамлены `---`,
        # то есть являются потоком из нескольких YAML-документов, и одиночный
        # safe_load ронял их с ComposerError (ложное срабатывание).
        list(yaml.safe_load_all(code))  # noqa: F821 - есть при HAVE_YAML
    except Exception as exc:  # noqa: BLE001 -- любая ошибка парсера = провал блока
        return f"{type(exc).__name__}: {str(exc).splitlines()[0]}"
    return None


def _sec_key(num: str) -> tuple[int, str] | None:
    """'2.2a' -> (2, 'a'); 'A' -> None. None = не числовая секция, не сравниваем."""
    m = re.fullmatch(r"(\d+)([a-z]*)", num)
    return (int(m.group(1)), m.group(2)) if m else None


def section_order(text: str) -> list[str]:
    """Секции, стоящие НЕ по порядку среди своих соседей.

    Зачем: anchor-правка markdown не знает про нумерацию, и новая секция ставится
    физически не туда — §8.6 перед §8.5.3, §3.1d перед §3.1c, §2.2b перед §2.2a,
    §7.2 перед §7.1. Случалось шесть раз, каждый ловился только глазами.

    Сравниваются ТОЛЬКО числовые соседи с общим родителем: буквенные метки секций
    (`### A. Первый заход`, `### B.`) в одном документе перемешаны с числовыми
    намеренно, и требовать от них порядка — ложное срабатывание.

    Заголовки внутри фенсов игнорируются: шаблоны содержат свои `## …`.
    Фенсы считаются ГЛУБИНОЙ и по `lstrip()` — как в blocks() выше. lab-11:
    blocks() починили по обеим осям (v1.33), а эта функция в том же файле
    осталась тумблером без lstrip — фенс с отступом сдвигал чётность, и
    дальше «внутри»/«снаружи» менялись местами: настоящие секции пропадали
    из проверки, заголовки шаблонов в неё попадали. Брат — не отдельный
    случай: у свойства «видит ли парсер фенс» два потребителя в этом файле,
    и правка обязана накрывать обоих.
    """
    problems: list[str] = []
    last: dict[str, tuple[int, str]] = {}
    depth = 0
    for line in text.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("```"):
            info = stripped[3:].strip()
            if depth == 0:
                depth = 1                      # открытие верхнего уровня
            elif info:
                depth += 1                     # вложенное открытие — с info-строкой
            else:
                depth -= 1                     # закрытие — голым фенсом
            continue
        if depth or not line.startswith("#"):
            continue
        m = re.match(r"#{2,4}\s+(?:⚠️?\s*)?([0-9A-Za-z.]+)\.\s", line)
        if not m:
            continue
        parts = m.group(1).split(".")
        key = _sec_key(parts[-1])
        if key is None:
            continue
        parent = ".".join(parts[:-1])
        prev = last.get(parent)
        if prev is not None and key < prev:
            problems.append(
                f"§{m.group(1)} стоит после §{parent + '.' if parent else ''}"
                f"{prev[0]}{prev[1]}"
            )
        if prev is None or key > prev:
            last[parent] = key
    return problems


def broken_tables(text: str) -> list[str]:
    """Строки таблицы, которые таблицей НЕ отрендерятся.

    Зачем: врезка `> …`, вставленная В СЕРЕДИНУ таблицы, съедает всё, что стоит
    после неё. Строка на `|` сразу за строкой на `>` — ленивое продолжение абзаца
    цитаты (CommonMark), то есть уезжает ВНУТРЬ врезки текстом с трубами. А если
    пустая строка есть, ряды образуют новую таблицу без заголовка — и это тоже не
    таблица. Найдено рендером: врезка про mutation стояла внутри каталога гейтов
    §3, и четыре гейта из шести (baseline-ratchet, new-dependency, ci-status,
    diff-coverage) не были строками таблицы, хотя §5 велит читать каталог
    построчно. Обе половины проверены: до переноса правило срабатывало ровно один
    раз на четыре канона, после — ни разу.

    Фенсы считаются глубиной и по `lstrip()` — как в blocks() и section_order():
    у свойства «видит ли парсер фенс» в этом файле уже три потребителя.
    """
    problems: list[str] = []
    depth = 0
    run: list[tuple[int, str]] = []
    prev = ""

    def flush() -> None:
        # Валидная таблица GFM: строка-заголовок, затем строка-разделитель.
        if len(run) >= 2 and not run[1][1].lstrip().lstrip("|").lstrip().startswith("--"):
            problems.append(f"строка {run[0][0]}: ряды без строки-разделителя")

    for i, line in enumerate(text.splitlines(), 1):
        stripped = line.lstrip()
        if stripped.startswith("```"):
            info = stripped[3:].strip()
            if depth == 0:
                depth = 1
            elif info:
                depth += 1
            else:
                depth -= 1
            prev = line
            continue
        if depth:
            prev = line
            continue
        if stripped.startswith("|"):
            if not run and prev.lstrip().startswith(">"):
                problems.append(f"строка {i}: ряд затянут во врезку `>` (нет пустой строки)")
            run.append((i, line))
        else:
            flush()
            run = []
        prev = line
    flush()
    return problems


def declared_versions(root: Path) -> tuple[dict[str, str], dict[str, str]]:
    """(версии из шапок канонов, версии из таблицы §1 карты)."""
    heads: dict[str, str] = {}
    for name in CANONS[1:]:
        p = root / name
        if not p.is_file():
            continue
        m = re.search(r"\*\*Canon version:\*\*\s*`([a-z]+)@([\d.]+)`", p.read_text(encoding="utf-8"))
        if m:
            heads[m.group(1)] = m.group(2)
    table: dict[str, str] = {}
    smap = root / CANONS[0]
    if smap.is_file():
        for m in re.finditer(r"\|\s*`([a-z]+)@([\d.]+)`\s*\|", smap.read_text(encoding="utf-8")):
            table[m.group(1)] = m.group(2)
    return heads, table


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    failures: list[str] = []
    total = 0

    for name in CANONS:
        path = root / name
        if not path.is_file():
            failures.append(f"{name}: MISSING")
            continue
        text = path.read_text(encoding="utf-8")
        found, unbalanced = blocks(text)
        if unbalanced:
            failures.append(f"{name}: unbalanced ``` fence (unterminated block)")
        checked = 0
        for line_no, lang, code in found:
            if lang not in CHECKED_LANGS or not code.strip():
                continue
            checked += 1
            total += 1
            err: str | None = None
            if lang == "python":
                try:
                    ast.parse(code)
                except SyntaxError as exc:
                    err = f"SyntaxError: {exc.msg} (block line {exc.lineno})"
            elif lang in {"bash", "sh"}:
                proc = subprocess.run(
                    ["bash", "-n"], input=code, text=True, capture_output=True, check=False
                )
                if proc.returncode:
                    err = proc.stderr.strip().splitlines()[-1] if proc.stderr.strip() else "bash -n failed"
            else:
                err = check_yaml(code)
            if err:
                failures.append(f"{name}:{line_no} [{lang}] {err}")
        for problem in section_order(text):
            failures.append(f"{name}: порядок секций — {problem}")
        for problem in broken_tables(text):
            failures.append(f"{name}: таблица не отрендерится — {problem}")
        print(f"{name}: {checked} executable block(s) checked")

    heads, table = declared_versions(root)
    for layer, ver in heads.items():
        if layer in table and table[layer] != ver:
            failures.append(
                f"version skew: {layer}@{ver} in canon header vs {layer}@{table[layer]} "
                f"in {CANONS[0]} §1 table"
            )
    missing = sorted(set(table) - set(heads))
    if missing:
        print(f"note: no Canon version header for {', '.join(missing)}")

    # Непокрытость называется в ИТОГОВОЙ строке, а не только в предупреждении выше:
    # именно итоговую строку копируют в отчёт и читают как «всё проверено».
    covered = f"{total} block(s)"
    if yaml_unparsed:
        covered += f" (из них {yaml_unparsed} yaml БЕЗ парсера — PyYAML не установлен)"
        print(
            "\n⚠ PyYAML не установлен: yaml-блоки проверены только на табы. "
            "Синтаксис YAML НЕ проверен — поставь PyYAML (pip install PyYAML), "
            "иначе битый конфиг проходит самопроверку молча.",
            file=sys.stderr,
        )
    print(f"\nstack_selftest: {covered}, {len(failures)} failure(s)")
    for f in failures:
        print(f"FAIL {f}", file=sys.stderr)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
