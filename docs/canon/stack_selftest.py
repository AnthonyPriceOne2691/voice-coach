#!/usr/bin/env python3
"""Self-test for the canon stack: every fenced code block must parse.

Usage:
  python stack_selftest.py [dir]

Проверяет:
  * python-блоки  -> ast.parse
  * bash-блоки    -> bash -n
  * yaml-блоки    -> yaml.safe_load (или запрет табов, если PyYAML нет)
  * json/toml     -> json.loads / tomllib.loads
  * сбалансированность ``` в каждом файле
  * версии в шапках канонов == таблица §1 в AGENT_STACK.md
  * объявленная стоимость чтения == измеренная (selftest_sizes, допуск ±10%)

Exit 0 = всё чисто. Exit 1 = хоть один блок не парсится / версии разошлись.
«Чисто» = чисто ПРОВЕРЕННОЕ: языки без парсера в stdlib (javascript, ini) и проза
(markdown, text) пропускаются — но пропуск ИМЕНУЕТСЯ числом с разбивкой в той же
итоговой строке. Измерено: 159 фенсов, 102 проверялось, 57 уходило МОЛЧА, и «Exit 0
= всё чисто» врало не неумением, а молчанием о нём.
"""

from __future__ import annotations

import ast
import json
import re
import subprocess
import sys
import tomllib
from collections import Counter
from pathlib import Path

import selftest_sizes

CANONS = (
    "AGENT_STACK.md",
    "AGENT_DELIVERY_HARNESS.md",
    "CODE_QUALITY_GATES.md",
    "OKF_KNOWLEDGE_BUNDLE.md",
)
# json/toml добавлены сюда парсерами из stdlib. javascript и ini НЕ добавлены
# намеренно: парсера в stdlib нет, а `node --check` сделал бы сьют зависимым от
# машины. Они уходят в счётчик пропущенного — названы, а не спрятаны.
CHECKED_LANGS = {"python", "bash", "sh", "yaml", "yml", "json", "toml"}


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
                # ⚠ Тело ВЫРАВНИВАЕТСЯ по отступу открывающего фенса, как это
                # делает `block_after` в извлекателе (`cqg@2.10`). До этого
                # `blocks()` хранил строки как есть, а извлекатель — тоже как
                # есть, но фенс с отступом вообще не видел: два поставляемых
                # парсера отвечали по-разному на вопрос «что здесь блок».
                # Выравнивание несущее: heredoc с отступом у терминатора не
                # закрывается, то есть непрогретый блок неисполним.
                buf.append(raw[pad:] if raw[:pad].isspace() else raw)
            continue
        info = line[3:].strip().lower()
        if lang is None:                       # открытие верхнего уровня
            lang, start, buf, depth = info, i, [], 1
            pad = len(raw) - len(line)
            continue
        if info:                               # вложенное открытие
            depth += 1
            buf.append(raw[pad:] if raw[:pad].isspace() else raw)
            continue
        depth -= 1                             # закрытие
        if depth == 0:
            out.append((start, lang, "\n".join(buf)))
            lang = None
        else:
            buf.append(raw[pad:] if raw[:pad].isspace() else raw)
    return out, (1 if lang is not None else 0)


#: Открытие heredoc: `<<TAG`, `<<'TAG'`, `<<"TAG"`, `<<-TAG`.
HEREDOC = re.compile(r"<<(-?)\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\2")


def unclosed_heredoc(code: str) -> str | None:
    """None = чисто. Терминатор heredoc, до которого не дойдёт shell.

    **`bash -n` этот класс НЕ ловит, и это замерено:** блок, где терминатор
    написан с отступом, синтаксически валиден — heredoc просто «доедает» файл
    до конца. То есть проверка печатала «исполняемый блок проверен» про блок,
    который исполниться не может.

    Найдено на собственной правке `cqg@2.09`: генератор провенанса в §5 шага 11
    лежал в нумерованном списке, терминатор `PY` шёл с отступом, `bash -n`
    молчал, и неисполнимость обнаружилась только прогоном блока оракулом.

    Терминатор обязан стоять в НУЛЕВОЙ колонке (для `<<-` допустимы табы —
    так определён сам оператор). Тело блока к этому моменту уже выровнено
    `blocks()` по отступу фенса, поэтому проверка судит то же, что исполнится.
    """
    # ⚠ Комментарии срезаются ДО поиска, и это не аккуратность. Первый же
    # прогон дал ложное срабатывание на строке канона `# пайп в `python -
    # <<heredoc` не работает` — то есть проверка обвинила блок за РАССКАЗ о
    # heredoc. Ложное срабатывание здесь дороже пропуска (§4.3b): такие
    # проверки чинят снятием, а эта только что завелась.
    bare = "\n".join(re.sub(r"(^|\s)#.*$", "", l) for l in code.splitlines())
    for dash, _q, tag in HEREDOC.findall(bare):
        allowed = rf"(?m)^\t*{tag}\s*$" if dash else rf"(?m)^{tag}\s*$"
        if not re.search(allowed, code):
            where = "с отступом" if re.search(rf"(?m)^\s+{tag}\s*$", code) else "отсутствует"
            return (f"heredoc <<{tag}: терминатор {where} — блок не закроется. "
                    "`bash -n` такое принимает, поэтому проверка отдельная")
    return None


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
    for name in CANONS:
        p = root / name
        if not p.is_file():
            continue
        # ⚠ ОБЕ формы шапки и дефис в имени (`cqg@2.12`). Здесь стояла только
        # форма `Canon version` и класс `[a-z]+`, то есть карта не читалась
        # дважды: ни по форме шапки, ни по имени `stack-map`. Цена этой слепоты
        # была названа в `field/fleet/build_versions.py` пределом «stack-map в
        # индекс НЕ попадает» — то есть версия карты не мерилась у флота вовсе.
        # Из четырёх реализаций этого понятия расходилась одна; остальные три
        # (`doctor_versions.py`, `tests/extract.py`, реестр классов) обе формы
        # читают. Согласие держит дифференциальный оракул.
        text = p.read_text(encoding="utf-8")
        m = (re.search(r"\*\*Canon version:\*\*\s*`([a-z-]+)@([\d.]+)`", text)
             or re.search(r"\*\*Эта карта:\*\*\s*`([a-z-]+)@([\d.]+)`", text))
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
    skipped: Counter[str] = Counter()

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
        gone: Counter[str] = Counter()
        for line_no, lang, code in found:
            if lang not in CHECKED_LANGS or not code.strip():
                # Здесь стоял голый `continue`, и это была вся находка: 57 фенсов
                # из 159 уходили без следа, а итог печатал только проверенные.
                # Теперь пропуск считается по языку — знаменатель обязан сходиться.
                gone["<empty>" if lang in CHECKED_LANGS else (lang or "<none>")] += 1
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
                err = unclosed_heredoc(code)
                if err:
                    pass
                elif proc.returncode:
                    err = proc.stderr.strip().splitlines()[-1] if proc.stderr.strip() else "bash -n failed"
            elif lang in {"json", "toml"}:
                # Оба декодера наследуют ValueError (JSONDecodeError, TOMLDecodeError).
                try:
                    (json.loads if lang == "json" else tomllib.loads)(code)
                except ValueError as exc:
                    err = f"{type(exc).__name__}: {str(exc).splitlines()[0]}"
            else:
                err = check_yaml(code)
            if err:
                failures.append(f"{name}:{line_no} [{lang}] {err}")
        skipped += gone
        for problem in section_order(text):
            failures.append(f"{name}: порядок секций — {problem}")
        for problem in broken_tables(text):
            failures.append(f"{name}: таблица не отрендерится — {problem}")
        print(f"{name}: {checked} executable block(s) checked, {sum(gone.values())} skipped")

    # Объявленная стоимость чтения против измеренной. Числа, по которым агент
    # решает, что НЕ открывать, до stack-map@1.43 расходились с фактом в 4.6 раза
    # и противоречили друг другу — механики, которая бы это ловила, не было.
    sizes: dict[str, tuple[int, int, int]] = {}
    last_sections: dict[str, str] = {}
    for name in CANONS:
        path = root / name
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        sizes[name] = selftest_sizes.measure(text)
        last = selftest_sizes.last_section(text)
        if last:
            last_sections[name] = last
        failures += [f"стоимость чтения — {p}" for p in
                     selftest_sizes.check_file(name, text)]
    smap = root / CANONS[0]
    if smap.is_file():
        failures += [f"стоимость чтения — {p}" for p in selftest_sizes.check_map(
            smap.read_text(encoding="utf-8"), sizes, last_sections)]

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
    covered = f"{total} block(s) checked"
    if yaml_unparsed:
        covered += f" (из них {yaml_unparsed} yaml БЕЗ парсера — PyYAML не установлен)"
        print(
            "\n⚠ PyYAML не установлен: yaml-блоки проверены только на табы. "
            "Синтаксис YAML НЕ проверен — поставь PyYAML (pip install PyYAML), "
            "иначе битый конфиг проходит самопроверку молча.",
            file=sys.stderr,
        )
    # Пропущенное стоит в ТОЙ ЖЕ строке, что и проверенное, а не отдельной: в отчёт
    # копируют итоговую строку, и отдельную можно не заметить. Разбивка по языкам
    # называет, ЧЕГО мы не умеем; сумма с проверенным = все верхнеуровневые фенсы.
    lost = ", ".join(f"{lang} {n}" for lang, n
                     in sorted(skipped.items(), key=lambda kv: (-kv[1], kv[0])))
    covered += f", {sum(skipped.values())} skipped" + (f" ({lost})" if lost else "")
    print(f"\nstack_selftest: {covered}, {len(failures)} failure(s)")
    for f in failures:
        print(f"FAIL {f}", file=sys.stderr)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
