#!/usr/bin/env python3
"""Delivery harness checker.

Usage:
  python scripts/delivery_check.py
  python scripts/delivery_check.py --require-spec

Exit 0 = OK (warnings allowed). Exit 1 = errors.
"""

from __future__ import annotations

import argparse
import functools
import json
import os
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DELIVERY = ROOT / "delivery"
ACTIVE = DELIVERY / "active"
ARCHIVE = DELIVERY / "archive"

# §3.4; переопределяются строкой в STATUS: "max_files_touched=40 reason=… by=human:…"
DEFAULT_BREAKERS = {"max_files_touched": 25, "max_loc_diff": 800}

# Процессные артефакты не считаются в breaker'ах: spec/plan/tasks и concept'ы —
# это не blast radius кода, а его описание. Механика самого контура — тоже:
# гейт-скрипты, их снимки, конфиги и workflow. Развёртывание контура и поставки
# `kind: refactor` по контуру (§9.1a прямо их предусматривает) трогают 15+ файлов
# и пробивали breaker всегда, превращая waiver в рутину — а рутинный waiver
# обесценивает механизм (§4.3a). Найдено развёртыванием, на handoff.
# Сами скрипты контура — тоже его механика, а не blast radius продукта. Их не было
# в списке, и три независимых развёртывания на настоящем проекте пробили breaker
# развёртыванием контура: `delivery_check.py` (946) + `delivery_metrics.py` (171) +
# `okf_validate.py` (113) + `okf_sync_gate.py` (297) = 1527 строк против лимита 800.
# «Разбей поставку» тут невыполним: один `delivery_check.py` больше лимита. Тот же
# класс уже был закрыт у гейта длины (его grep исключает эти четыре пути) и не
# перенесён сюда — правка была на СЛУЧАЙ, а не на класс.
BREAKER_EXCLUDE = (
    "delivery/",
    "knowledge/",
    "scripts/lint/",
    "scripts/merge_guard.sh",
    "scripts/delivery_check.py",
    "scripts/delivery_metrics.py",
    "scripts/okf_validate.py",
    "scripts/okf_sync_gate.py",
    # `.claude/` — механика контура (права агента §4.5), а не продуктовый код.
    # Без исключения маячок §12.5 срабатывал на классе «безопасность» из-за
    # слова `permission` в собственном файле настроек прав: контур ругался на
    # свою же машинерию. Найдено на первом прогоне маячка (арена lab-10).
    ".claude/",
    # Снимок канонов варианта C (§7.1 AGENT_STACK) — механика контура, а не код
    # продукта: 10 743 строки из 13 743 пробитого лимита давал именно он. §7.1 велит
    # «проверь, что путь снимка в BREAKER_EXCLUDE» — а его тут не было: инструкцию
    # добавили, путь забыли. Нашло приёмочное развёртывание.
    "docs/canon/",
    ".pre-commit-config.yaml",
    ".github/workflows/",
    ".claude/",
)


# Текстовые расширения для поиска id примеров в тестах. Маска `*test*` ловит и
# `tests/__pycache__/test_x.cpython-314.pyc` — бинарник, на котором чтение падало
# и роняло весь гейт (полевая находка F9: воспроизводится в любом проекте, где
# хоть раз запускали pytest).
TEST_TEXT_SUFFIXES = (
    ".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".rs", ".swift", ".kt", ".java",
    ".rb", ".php", ".cs", ".md",
)
SKIP_DIR_PARTS = ("__pycache__", ".venv", "node_modules", ".mypy_cache", ".pytest_cache")


def read(path: Path) -> str:
    """Текст файла или "".

    `errors="replace"` — не косметика: фазовый гейт не имеет права падать
    трейсбеком про кодек на файле, который он читает попутно. Отказ гейта хуже
    его ошибки: в CI шаг красный по причине, не связанной с поставкой.
    """
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def git(*args: str) -> str:
    """git с подавлением ошибок: пустая строка = не смог."""
    try:
        out = subprocess.run(["git", *args], capture_output=True, text=True, check=False)
    except FileNotFoundError:
        return ""
    return out.stdout if out.returncode == 0 else ""


def signature_verdict(name: str, raw: str, klass: str, phase: str) -> tuple[list[str], list[str]]:
    """§2.2b для ЛЮБОГО поля-подписи: `yes` / `deferred (reason=…)` / нет.

    Правило одно на класс полей, а не на одно имя. Дыру «человека нет, и канон про
    это молчит» закрыли для `human_ok_spec` — и она вернулась в `human_ok_plan`,
    потому что там стояла отдельная ветка с той же логикой минус `deferred`. Пока
    смысл один, а кода два, третье поле повторит историю.

    `deferred` не ослабляет проверку, а переносит её на мерж: до converge включительно
    работа идёт под запись долга, на handoff требуется `yes`.
    """
    value = raw.lower()
    errs: list[str] = []
    warns: list[str] = []
    if value.startswith("deferred"):
        if phase == "handoff":
            errs.append(
                f"class {klass} at handoff: {name} всё ещё deferred (§2.2b) — долг по "
                "подписи закрывается ДО мержа: покажи человеку и поставь yes (by=… at=…)"
            )
        elif "reason=" not in value:
            errs.append(
                f"{name}: deferred без reason= (§2.2b) — «человек недоступен» надо "
                "назвать, иначе это тихий обход"
            )
        else:
            warns.append(
                f"class {klass}: {name} deferred — ещё никем не подписано (§2.2b); "
                "долг закрывается до handoff"
            )
    elif not (value.startswith("yes") or "human:" in value):
        # Подпись — это `yes (by=human:…)` ИЛИ прямое `human:<имя> at=…`: у полей
        # разная форма (`human_ok_spec` против `asserts_reviewed_by`), а смысл один.
        # Проверять только префикс `yes` значило бы краснеть на канонной форме
        # второго поля — ложное срабатывание, которое §4.3b называет дефектом гейта.
        errs.append(
            f"class {klass} at phase={phase}: {name} без подписи человека "
            "(stop-gate §3.3; `yes (by=human:…)` или `human:<имя> at=…`; "
            "человека нет — deferred (reason=…), §2.2b)"
        )
    return errs, warns


def diff_stats(base: str) -> tuple[int, int, int, int, list[str]] | None:
    """(files, added, deleted, excluded, paths) для base..HEAD; None если ref недоступен.

    `paths` — только код: процессные артефакты отфильтрованы тем же
    BREAKER_EXCLUDE, потому что оба потребителя (breaker'ы §3.4 и сопоставление
    уроков §2.2a) спрашивают про изменения в коде, а не в его описании.
    """
    if not git("rev-parse", "--verify", "--quiet", base).strip():
        return None
    merge_base = git("merge-base", base, "HEAD").strip() or base
    files = added = deleted = excluded = 0
    paths: list[str] = []
    for line in git("diff", "--numstat", f"{merge_base}..HEAD").splitlines():
        parts = line.split("\t")
        if len(parts) != 3:
            continue
        a, d, path = parts
        if path.startswith(BREAKER_EXCLUDE):
            excluded += 1
            continue
        files += 1
        paths.append(path)
        added += int(a) if a.isdigit() else 0      # "-" у бинарников
        deleted += int(d) if d.isdigit() else 0
    return files, added, deleted, excluded, paths


def archive_index_rows(text: str) -> list[tuple[list[str], list[str]]]:
    """[(префиксы путей, id уроков)] из таблицы A.13.

    Разбор построчный по markdown-таблице: строка шапки и разделитель отсеиваются
    сами — в них нет backtick'ов, а значит и путей. Формат жёсток ровно в двух
    колонках (пути в backticks, id вида L<N>), чтобы правило §2.2a было
    исполнимым, а не пожеланием.
    """
    rows: list[tuple[list[str], list[str]]] = []
    for line in text.splitlines():
        if not line.lstrip().startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 4:
            continue
        prefixes = [p for p in re.findall(r"`([^`]+)`", cells[2]) if "/" in p]
        if prefixes:
            rows.append((prefixes, re.findall(r"\bL\d+\b", cells[3])))
    return rows


def applicable_lessons(index_text: str, changed: list[str]) -> list[str]:
    """id уроков из строк, чьи пути пересекаются с диффом (порядок сохранён)."""
    out: list[str] = []
    for prefixes, ids in archive_index_rows(index_text):
        if any(c.startswith(p) for p in prefixes for c in changed):
            out.extend(ids)
    return list(dict.fromkeys(out))


def permission_block(constitution: str) -> dict[str, list[str]] | None:
    """Блок `agent-permissions` из CONSTITUTION (§4.5); None = блока нет.

    `allow` не разбираем сознательно: сверять накопительный список конкретных
    команд = постоянное ложное срабатывание (§4.3b, случай 1). `sandbox` (§4.6) —
    переводы из HITL в автономию, они не сверяются с настройками, а проверяются на
    существование оракула.
    """
    m = re.search(r"```(?:text)?\n[ \t]*agent-permissions[ \t]*\n(.*?)```", constitution, re.S)
    if not m:
        return None
    out: dict[str, list[str]] = {"deny": [], "ask": [], "sandbox": []}
    for raw in m.group(1).splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        # partition по ПЕРВОМУ двоеточию: сами правила его содержат
        # ("deny: Bash(git push --force:*)").
        key, _, rule = line.partition(":")
        if key.strip() in out and rule.strip():
            out[key.strip()].append(rule.strip())
    return out


# Незаполненный шаблон не должен проходить проверку — тот же урок, что с STATUS
# в v1.5 («class: <S|M|L>» читался как class=S). Плейсхолдер здесь — угловые
# скобки со СЛОВОМ внутри: `<гипотеза>`, `<название>`, `<X>`. Сужение до кириллицы
# или одиночной заглавной сделано нарочно, чтобы не считать плейсхолдерами
# законные `List<int>` и `<100ms` в тексте решения.
PLACEHOLDER_RE = re.compile(r"<[^<>]*(?:[А-Яа-яЁё][^<>]*|[A-Z])>")


def unfilled(line: str) -> bool:
    """Строка — ещё шаблон, а не содержание."""
    return bool(PLACEHOLDER_RE.search(line))


def list_entries(text: str) -> list[str]:
    """Логические записи списка: продолжения переноса склеены с их пунктом.

    Разбор по ФИЗИЧЕСКИМ строкам делал вердикт гейта зависимым от вёрстки: одно и
    то же решение проходило при переносе после «потому что» и краснело при переносе
    перед ним. Канонному примеру §12.2 повезло, записи исполнителя — нет. Тот же
    класс независимо нашли два развёртывания, в разных файлах (`decisions.md` и
    `plan.md`), поэтому склейка живёт здесь одна на всех потребителей.

    Продолжение — строка, которая не начинает новый пункт и не пуста; отступ не
    требуем: markdown его прощает, а люди и агенты пишут по-разному.
    """
    entries: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if re.match(r"^[-*]\s+\S", line):
            entries.append(line)
        elif line and entries and not line.startswith("#") and not line.startswith("```"):
            entries[-1] += " " + line
    return entries


def decision_lines(text: str) -> tuple[list[str], list[str]]:
    """(валидные, битые) решения §12.2.

    Кандидат — только list-item: проза и заголовки в файле не проверяются.
    Валидная запись называет альтернативу И причину; без альтернативы это отчёт о
    сделанном, по которому аудит провести нельзя. Записи шаблона не попадают ни в
    один список: они не решения, но и ругаться на них как на битый формат нельзя.
    """
    ok: list[str] = []
    bad: list[str] = []
    for line in list_entries(text):
        if unfilled(line):
            continue
        low = line.lower()
        has_alt = "вместо" in low or "instead of" in low
        has_why = "потому что" in low or "because" in low
        (ok if (has_alt and has_why) else bad).append(line)
    return ok, bad


# Цена решения, а не предпочтение. «Выбрал A вместо B — потому что дешевле» формат
# §12.2 проходит, но **неопровержимо**: проверить это нельзя ни человеком, ни машиной,
# значит запись не даёт аудита, ради которого она и ведётся. «B потребовал бы миграции
# 40k строк» человек проверяет за секунды.
#
# ⚠ Признак — НЕ список глаголов. Первая версия (delivery@1.38) держала список
# «требует / ломает / зависит / переписать / миграц…», и он ошибался в обе стороны:
# обходился дописыванием слова, а хорошую запись отвергал. На dogfooding'е (lab-10)
# он пометил «без цены» решение, где следствие названо предельно конкретно — «длина
# съедала легитимное `First one. Second one?`», — просто глагола «съедала» в списке
# не было. Ложное срабатывание на своей же проверке в тот же день, когда она введена.
#
# Признак — СОЮЗ трёх, а не замена. Первая попытка правки была «только цитата из
# диффа», и она неверна по построению: **дифф содержит то, что выбрали, а не то, что
# отвергли**. Цена отвергнутого варианта естественно ссылается на то, чего в коде
# НЕТ («B требует внешнего сервиса, которого у нас нет», «B потребовал бы миграции»),
# и такая запись — образцовая, а проверка её отвергала. Поймал существующий тест.
#
# Поэтому: число ИЛИ цитата из диффа ИЛИ маркер следствия. Союз даёт наименьшую долю
# ложных срабатываний, и «дешевле» им всё равно не удовлетворить. По нашему критерию
# «кто здесь может поймать ложь» ответ — человек за секунды, значит задача проверки
# не принуждать, а придать записи форму, в которой ложь видна. Отсюда предупреждение,
# не ошибка, и широкий признак вместо узкого.
COST_MARKERS = (
    "требует", "требовал", "ломает", "сломал", "съедал", "съест", "зависит",
    "недоступ", "не поддерж", "переписать", "миграц", "потерял", "нет доступа",
    "запрещ", "нет в", "пришлось бы", "потребовал",
)

DECISION_STOPWORDS = frozenset(
    "test tests main init app src lib code file data self none true false "
    "type name path text line list dict json yaml toml".split()
)


def diff_identifiers(paths: list[str]) -> set[str]:
    """Токены, которые есть в диффе: базовые имена файлов + идентификаторы кода.

    Берём и пути, и содержимое изменённых строк: решение может ссылаться и на файл
    («вынес в sentences.py»), и на функцию («`_cut_points` считает границы»).
    """
    ids: set[str] = set()
    for path in paths:
        for part in re.split(r"[/\\.]", path):
            if len(part) >= 4 and part.lower() not in DECISION_STOPWORDS:
                ids.add(part.lower())
    body = git("diff", "--unified=0", "HEAD~1..HEAD", "--", *paths) if paths else ""
    for tok in re.findall(r"[A-Za-z_][A-Za-z0-9_]{3,}", body):
        low = tok.lower()
        if low not in DECISION_STOPWORDS:
            ids.add(low)
    return ids


def decisions_without_cost(text: str, diff_ids: set[str] | None = None) -> list[str]:
    """Решения, где цена не названа ни числом, ни ссылкой в код.

    `diff_ids=None` — дифф недоступен (нет ref'а, не git-репозиторий). Тогда
    судить нечем, и проверка молчит: предупреждение по неверной причине хуже его
    отсутствия — оно учит игнорировать этот гейт.
    """
    if diff_ids is None:
        return []
    out = []
    for line in decision_lines(text)[0]:
        # ⚠ Дата записи выкидывается ДО поиска числа. Формат §12.2 — «- <дата> ·
        # решение», поэтому цифры есть в КАЖДОЙ валидной записи, и наивный поиск
        # числа не срабатывал бы никогда. Третий случай этого класса за сессию:
        # хвост версии читался как количество, а цифра из id примера `A1`
        # закрывала проверку `observability: 2+`. Число надо искать там, где оно
        # что-то значит.
        body = re.sub(r"^\s*[-*]?\s*\d{4}-\d{2}-\d{2}\s*[·:—-]?\s*", "", line)
        if re.search(r"(?<![A-Za-z])\d", body):
            continue  # число — самая проверяемая форма цены
        low = body.lower()
        if any(m in low for m in COST_MARKERS):
            continue  # названо следствие
        words = {w.lower() for w in re.findall(r"[A-Za-zА-Яа-яЁё_][\w-]{3,}", body)}
        if words & diff_ids:
            continue  # цитирует код — такое не напишешь, не открыв дифф
        out.append(line)
    return out


def read_json(path: Path) -> tuple[dict, str]:
    """(данные, ошибка). Битый файл настроек — сама по себе находка, а не пустой dict."""
    if not path.is_file():
        return {}, ""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return {}, f"{type(exc).__name__}: {str(exc).splitlines()[0]}"
    return (data if isinstance(data, dict) else {}), ""


def field(status: str, name: str) -> str:
    """Значение поля STATUS: "- **class:** M" -> "M". Inline-комментарий срезается."""
    m = re.search(rf"(?im)^[ \t]*[-*]?[ \t]*\**{name}\**[ \t]*:\**[ \t]*(.*)$", status)
    if not m:
        return ""
    return re.sub(r"<!--.*?-->", "", m.group(1)).strip()


# Голый список коротких альтернатив: ВСЯ строка — токены ≤16 символов через `|`.
# Это форма необработанного шаблона ("S | M | L"), а не выбранного значения.
BARE_CHOICES_RE = re.compile(r"^[\w/.\-]{1,16}(?:\s*\|\s*[\w/.\-]{1,16})+$")


def is_placeholder(value: str) -> bool:
    """Незаполненный шаблон: "<S|M|L>", "S | M | L", "…", пусто.

    Вертикальная черта — признак шаблона ТОЛЬКО в форме голого списка коротких
    альтернатив: "S | M | L" не может быть выбранным значением, и без этой
    проверки класс L проезжал бы мимо требований spec/plan (§2.2).

    Просто «есть |» признаком НЕ является: is_placeholder зовут 14 полей, и
    часть из них свободнотекстовые. lab-11 F7: точный observe_signal с
    jq-конвейером (`docker logs app | jq …`) объявлялся «пустым» — гейт
    наказывал точность, а сообщение врало направлением. Сегменты конвейера
    многословны, поэтому голый список коротких альтернатив их не ловит.
    Область применимости признака — решение, а не деталь реализации; обе
    стороны закреплены тестами (тот же класс, что фильтр блочных скаляров
    в check_gate_coverage.sh, cqg@1.40).
    """
    if not value or value in {"…", "...", "-", "TBD", "tbd"}:
        return True
    return value.startswith("<") or bool(BARE_CHOICES_RE.match(value))


VERDICT_RE = re.compile(r"(?i)ОПРОВЕРГНУТА|ПОДТВЕРЖДЕНА|refuted|confirmed")
# Начало структурного блока: пункт списка, строка таблицы, заголовок.
# `\|\s*` а не `\|`: в таблице после вертикальной черты стоит пробел, и
# требование непробела сразу за ней отвергало ровно тот формат, ради
# которого правка и делалась.
BLOCK_START = re.compile(r"^\s*(?:[-*+]\s+|\|\s*|#{1,6}\s+)\S")


def verdict_blocks(text: str) -> list[str]:
    """Блоки диагноза, содержащие заполненный вердикт (§12.1).

    Считаются БЛОКИ, а не строки, и это не косметика. Прежняя версия требовала
    вердикт на той же физической строке, что маркер списка, — из-за чего отвергала
    и таблицу «гипотеза | вердикт», и пункт с переносом строки. На dogfooding'е
    (lab-10) я споткнулся об это дважды в одном файле, и оба раза сообщение
    говорило «вердиктов нет», хотя вердикты в файле были: диагноз про содержание,
    когда причина в форме.

    Ограничение, которое СОХРАНЯЕТСЯ: проза о формате вердиктом не считается. В
    шаблоне A.15 есть строка «Вердикты: `ОПРОВЕРГНУТА` / `ПОДТВЕРЖДЕНА`» — она не
    начинается структурным маркером, поэтому в блок не попадает. Ровно от неё
    ограничение и защищало.
    """
    blocks: list[str] = []
    cur: list[str] | None = None
    for raw in text.splitlines():
        if BLOCK_START.match(raw):
            if cur:
                blocks.append("\n".join(cur))
            cur = [raw.strip()]
        elif cur is not None and raw.strip() and raw.startswith((" ", "\t")):
            cur.append(raw.strip())  # продолжение пункта
        else:
            if cur:
                blocks.append("\n".join(cur))
            cur = None
    if cur:
        blocks.append("\n".join(cur))
    return [b for b in blocks if VERDICT_RE.search(b) and not unfilled(b)]


# --- Маячки на рисковый дифф (§12.5) ----------------------------------------
# Есть класс дефектов, у которых НЕТ оракула: архитектура выбрана неудачно, функция
# делает не то, что нужно. Механика такое не судит, и притворяться, что судит, —
# худшее из решений (см. §3.1d, врезка про отказ от оценки решений моделью).
#
# Что здесь делается вместо: не оценка качества, а **маршрутизация** — гарантия, что
# рисковый дифф кто-то ПРОЧИТАЛ, и след этого прочтения остался.
#
# ⚠ «Человек посмотрел» проверить нельзя: у этого заявления нет наблюдения для
# сверки, и требовать его — значит завести анкету. А вот «кто-то прочитал ИМЕННО
# ЭТОТ дифф» — можно: запись обязана цитировать идентификаторы, которые в диффе
# реально есть. Тот же приём, что `repro_test:` (не «ты тестировал?», а «тест
# существует и падает без фикса») и что признак цены решения (§12.2a).
#
# Чего это НЕ даёт, и это надо говорить прямо: доказательства, что смотрел ЧЕЛОВЕК,
# здесь нет. Есть доказательство, что дифф прочитан. Для конфигурации «один
# владелец + агенты» это достижимый потолок, и он всё равно ценен: чтение вынуждено,
# а запись владелец просматривает за секунды. Обойти можно, выгрепав идентификаторы,
# но это дороже, чем прочитать маленький дифф, и видно при просмотре.
RISK_CLASSES = {
    "деньги": r"(?i)\b(price|pricing|payment|invoice|balance|refund|billing|amount|"
              r"цена|платеж|платёж|баланс|счёт)\w*",
    # ⚠ Русские корни — только однозначные. `доступ` пришлось убрать: он совпадал
    # внутри слова `недоступен` в обычном комментарии, и маячок требовал ревью
    # безопасности от правки текстового чанкера. Ложное срабатывание от ФРАГМЕНТА,
    # а не от смысла; поймано на первом же прогоне маячка (арена lab-10).
    # Только СОСТАВНЫЕ формы там, где слово многозначно: `token` в этом проекте —
    # токен стрима LLM, и голый `\btoken` совпадал в `test_..._one_token`, требуя
    # ревью безопасности от правки текстового чанкера. На проекте, чей домен —
    # токены, такой маячок сработал бы на каждом диффе и был бы снят через неделю.
    "безопасность": r"(?i)(\bauth|access_token|auth_token|api_token|refresh_token|"
                    r"\bbearer|\bsecret|\bpassword|\bcredential|\bpermission|"
                    r"\bjwt\b|session_key|парол|авториз)",
    "транзакция БД": r"(?i)\b(commit|rollback|transaction|begin\(\)|savepoint|"
                     r"session\.begin|atomic)\w*",
    # lab-12: единственный класс, подтверждённый как slipped ОБЕИМИ арками, —
    # CPU-bound работа по всей выборке в async-хендлере. Маячок его тогда поднял,
    # но ПО ЧУЖОМУ ПОВОДУ («новый модуль» + `commit` у соседа в репозитории):
    # замер показал «classes matching perf/limit/scan: []». Та же правка в
    # СУЩЕСТВУЮЩЕМ модуле не подняла бы маячок вовсе.
    #
    # Признак — не слово «медленно», а ФОРМА: выборка без границы (`list_all`,
    # `.all()`, `fetchall`, `select(...)` без `limit`) и разбор/поиск в цикле.
    # Слова однозначные и составные, по правилу выше: голый `all` или `loop`
    # совпадал бы всюду и снял бы маячок за неделю.
    "производительность": r"(?i)(\blist_all\b|\bfetchall\b|\.all\(\)|"
                          r"scan_all|full_scan|\bselectinload\b|"
                          r"json\.loads|json\.dumps|\bre\.(search|compile|finditer)\b)",
    "цепочка гейтов": r"scripts/lint/|merge_guard|pre-commit-config",
    "интеграция": r"(?i)\b(httpx|requests\.|aiohttp|urllib|webhook|grpc|boto3|"
                  r"openai|anthropic)\w*",
}


def risky_classes(paths: list[str], base: str) -> dict[str, set[str]]:
    """Классы риска, которых коснулся дифф → чем именно они подняты.

    Возвращается не список имён, а КЛАСС → ТОКЕНЫ, которые его подняли
    (`производительность` → `{list_all, json.loads}`). Токены нужны проверке
    ниже: назвать класс можно и его именем, и тем, что его вызвало, — второе
    честнее, потому что показывает, что читатель видел конкретное место.
    """
    if not paths:
        return {}
    body = git("diff", "--unified=0", f"{base}..HEAD", "--", *paths)
    haystack = "\n".join(paths) + "\n" + body
    hits: dict[str, set[str]] = {}
    for name, pat in RISK_CLASSES.items():
        found = {m.group(0).lower() for m in re.finditer(pat, haystack)}
        if found:
            hits[name] = found
    # Новый модуль — отдельный класс: у него ещё нет ни одного читателя.
    # Токены — имена самих новых файлов: сказать «`transcripts.py` — чистые
    # функции, состояния нет» и есть разбор этого класса.
    added = {
        Path(p).stem.lower()
        for p in paths
        if p.endswith((".py", ".ts", ".tsx"))
        and git("log", "--diff-filter=A", "--format=%H", f"{base}..HEAD", "--", p).strip()
    }
    if added:
        hits["новый модуль"] = added
    return hits


def risk_review_gaps(
    report: str, classes: dict[str, set[str]], diff_ids: set[str]
) -> list[str]:
    """Чего не хватает в записи ревью рисковых мест.

    Требуется НЕ подтверждение, а содержание: назван класс и процитировано то, что
    в диффе есть. Законный выход — «риска нет, потому что …» с теми же цитатами:
    он тоже требует чтения, поэтому это не waiver и не галочка.
    """
    if not classes:
        return []
    block = re.search(
        r"(?ims)^#{1,4}\s*(?:ревью\s+рисковых|risk\s+review)\b.*?(?=^#{1,4}\s|\Z)",
        report,
    )
    if not block:
        return [
            "нет блока «## Ревью рисковых мест» (§12.5) — дифф задел: "
            + ", ".join(classes)
            + ". Гейта на это нет и быть не может: у «архитектура неудачна» нет "
              "оракула. Нужно НЕ подтверждение, что смотрел, а содержание: что "
              "именно может сломаться, с именами из диффа. Риска нет — так и "
              "напиши «риска нет, потому что …», тоже с именами"
        ]
    body = block.group(0)
    low = body.lower()
    gaps = []
    words_of = lambda t: {w.lower() for w in re.findall(r"[A-Za-z_][A-Za-z0-9_]{3,}", t)}

    # КАЖДЫЙ задетый класс обязан быть разобран, а не «хотя бы один».
    #
    # Было «один класс где угодно в блоке + ≥2 цитаты где угодно» — это покупало
    # заголовок, а не содержание: lab-12 показала пробой, что проходят и
    # трёхстрочный блок с одним классом, и настоящий блок, из которого удалили
    # ровно перф-строку. Отписка по частям — тот же класс, что отписка целиком.
    #
    # ⚠ Класс считается разобранным ДВУМЯ способами: назвали его имя ИЛИ назвали
    # тот токен, который его поднял (`list_all`, `session.begin`, имя нового
    # модуля). Второе честнее имени: оно показывает, что читатель видел
    # конкретное место, а не переписал ярлык. И это снимает хрупкость: требовать
    # дословного русского ярлыка в каждой строке значило бы краснить осмысленную
    # запись — ровно та ловушка §4.3b, из-за которой первая версия этой правки
    # покраснела на собственном тесте «законный выход» (класс «новый модуль»
    # структурный, его никто не называет словами).
    # «новый модуль» из требования исключён СОЗНАТЕЛЬНО: он структурный — поднимает
    # маячок (заставляет написать блок), но своей строки не требует, потому что
    # разбор любого места нового файла и есть его разбор. Требование отдельной
    # строки под него краснило бы осмысленные записи — поймано собственным тестом
    # «законный выход» на первой версии правки.
    STRUCTURAL = {"новый модуль"}
    undiscussed = [
        c for c, tokens in (classes or {}).items()
        if c not in STRUCTURAL
        and c.lower() not in low
        and not any(t in low for t in tokens)
    ]
    if undiscussed:
        gaps.append(
            "в блоке ревью не разобран(ы) задетый(е) класс(ы) риска: "
            + ", ".join(undiscussed)
            + " (§12.5) — на каждый нужна строка: либо чем он опасен здесь, либо "
            "«риска нет, потому что …». Достаточно назвать то, что его подняло "
            "(функцию, поле, файл из диффа) — ярлык переписывать не обязательно"
        )

    cited = words_of(body) & diff_ids
    if len(cited) < 2:
        gaps.append(
            f"в блоке ревью {len(cited)} цитат(ы) из диффа, нужно ≥2 (§12.5) — "
            "«проверил, всё ок» проверить нельзя ничем; назови функции, поля или "
            "файлы, которые смотрел: этого не написать, не открыв дифф"
        )
    return gaps


# --- Происхождение ожидания (§3.1d) -----------------------------------------
# §3.1d говорит: «примеры пишутся на фазе specify, ДО plan и до кода. Порядок
# принципиален: ожидание, придуманное после реализации, — это описание реализации».
# До delivery@1.38 это принуждалось НИЧЕМ: проверялось наличие блока, наличие id и
# ссылки на них в тестах — то есть три признака, ни один из которых не про порядок.
#
# Память — история git, как в §3.5. Ищем `git log -S<id>`: коммиты, где менялось
# число вхождений строки. Самый старый — тот, где id появился.
#
# ⚠ ТРИ исхода, а не два, и это не мягкость. Агент часто кладёт спеку, код и тесты
# ОДНИМ коммитом; требовать «спека строго старше» значило бы краснеть рутинно, и
# проверку сняли бы (класс F4/F6/F13). Когда всё в одном коммите, порядок
# установить НЕЛЬЗЯ — честный ответ «не проверить», а не «нарушение». Считается и
# печатается числом: это подсказывает коммитить спеку отдельно, ничего не ломая.
def _first_commit_with(text: str, *paths: str) -> str:
    """Самый старый коммит, где появился ТОКЕН `text` в указанных путях.

    Токен, а не подстрока, и это не педантизм. lab-12: id примеров короткие
    (`A2`), а `-S` считает вхождения подстроки — `A2` совпадал внутри
    `DATA2_FIXTURE` в legacy-тесте, закоммиченном задолго до поставки. Итог:
    ложное «пример появился ПОЗЖЕ теста», то есть обвинение в худшем
    процессном грехе (ожидание придумано после кода) на честной работе.
    Исполнителю его не снять ничем, кроме переименования id, — что одна арка и
    сделала, порвав связь с id, подписанными заказчиком. **Канон учил себя
    обходить**, а обход стоил ровно того, ради чего проверка и написана.

    ⚠ Граница — явный класс символов, а НЕ `\\b`. Замерено: `-S'\\bA2\\b'
    --pickaxe-regex` в git не находит НИЧЕГО, то есть очевидная правка сделала
    бы проверку МЁРТВОЙ — хуже исходного дефекта, и обратный прогон «сломано →
    падает» этого бы не показал (падало бы и там, и там). Тот же класс, что
    `\\b` в awk и `^\\+` в ugrep.
    """
    if not paths:
        return ""
    token = rf"(^|[^A-Za-z0-9_]){re.escape(text)}([^A-Za-z0-9_]|$)"
    out = git("-C", str(ROOT), "log", "--format=%H", f"-S{token}",
              "--pickaxe-regex", "--", *paths)
    revs = [l.strip() for l in out.split("\n") if l.strip()]
    return revs[-1] if revs else ""


def expectation_predates_tests(ex_ids: list[str], test_paths: list[str]) -> list[str]:
    """[(предупреждения)] — порядок «пример раньше теста» по истории.

    Возвращает предупреждения, а не ошибки: до первого живого проекта у нас нет
    данных, как часто «не проверить» встречается в норме. Ужесточать — после
    замера, а не из симметрии.
    """
    if not ex_ids or not test_paths:
        return []
    order = {rev: i for i, rev in enumerate(
        git("-C", str(ROOT), "rev-list", "--topo-order", "HEAD").split())}
    if not order:
        return []
    spec_rel = "delivery/active/spec.md"
    after, unknown = [], []
    for ex in dict.fromkeys(ex_ids):
        s_rev = _first_commit_with(ex, spec_rel)
        t_rev = _first_commit_with(ex, *test_paths)
        if not s_rev or not t_rev:
            continue  # id ещё не в истории — поставка не закоммичена, не наше дело
        if s_rev == t_rev:
            unknown.append(ex)
        elif order.get(s_rev, 0) < order.get(t_rev, 0):
            # Меньший индекс = НОВЕЕ. Пример новее теста — ожидание дописали после.
            after.append(ex)
    msgs = []
    if after:
        msgs.append(
            "§3.1d: примеры появились в истории ПОЗЖЕ ссылающихся на них тестов: "
            f"{', '.join(after)}. Ожидание, придуманное после реализации, — это "
            "описание реализации, и все гейты ниже проверяют его согласие с самим "
            "собой. Такой пример надо переписать от задачи, а не от кода"
        )
    if unknown:
        msgs.append(
            f"§3.1d: у {len(unknown)} из {len(dict.fromkeys(ex_ids))} примеров "
            f"порядок не проверить — пример и тест приехали одним коммитом "
            f"({', '.join(unknown[:5])}). Это не нарушение, но и не доказательство: "
            "коммить спеку отдельным коммитом до кода, тогда порядок виден"
        )
    return msgs


# --- Долг во времени (§3.5) -------------------------------------------------
# Гейты смотрят на один коммит, а вырождение — это тренд. Ратчет запрещает снимку
# РАСТИ и ничего не говорит про то, что он стоит на месте: двадцать поставок с
# неподвижным снимком зелёные все двадцать, и формально никто не нарушил. Платить
# по долгу заставляет только соглашение «тронул легаси — почисти часть», то есть
# честность исполнителя: не заметил или схалтурил — запись живёт вечно.
#
# ПАМЯТЬЮ СЛУЖИТ ИСТОРИЯ GIT, а не отдельный файл. Свою «тетрадку» валидатора
# можно поправить тем же коммитом, что и нарушение, — снаружи всё сойдётся, и
# подделывать даже не надо, достаточно пересчитать. Историю так не поправишь:
# нужно переписать прошлое, а это видно. Точки замера — коммиты, добавившие
# каталоги в `delivery/archive/`: они и есть отметки «поставка закрыта».
DEBT_WINDOW = int(os.environ.get("DEBT_WINDOW", "5"))
BASELINE_GLOB = "scripts/lint/*_baseline.txt"
# Формат снимков всех ратчет-гейтов один: `<число>:<путь>`. Агрегатные строки
# (`py_total=0 js_critical=0`) записями долга не являются и не считаются.
DEBT_ENTRY = re.compile(r"^(\d+):(.+)$")


def debt_entries(blob: str) -> dict[str, int]:
    """{путь: вес} из текста одного снимка. Комментарии и секции пропускаются."""
    out: dict[str, int] = {}
    for line in blob.splitlines():
        m = DEBT_ENTRY.match(line.strip())
        if m:
            out[m.group(2)] = out.get(m.group(2), 0) + int(m.group(1))
    return out


@functools.lru_cache(maxsize=None)
def _debt_at_cached(rev: str) -> tuple[tuple[str, int], ...]:
    """Кэш на ревизию: одна и та же точка окна читается дважды (сумма и возраст),
    а каждое чтение — это `git ls-tree` плюс `git show` на снимок."""
    total: dict[str, int] = {}
    # `-C ROOT` обязателен: `ROOT` берётся от пути скрипта, а `git` без него
    # работал бы в ТЕКУЩЕМ каталоге. В продакшене они совпадают, но проверка,
    # правильность которой зависит от того, откуда её позвали, — не проверка.
    names = git("-C", str(ROOT), "ls-tree", "--name-only", "-r", rev,
                "scripts/lint/").split()
    for name in names:
        if not name.endswith("_baseline.txt"):
            continue
        for path, weight in debt_entries(
                git("-C", str(ROOT), "show", f"{rev}:{name}")).items():
            total[path] = total.get(path, 0) + weight
    return tuple(sorted(total.items()))


def debt_at(rev: str) -> dict[str, int]:
    """Долг на ревизии: объединение снимков всех гейтов."""
    return dict(_debt_at_cached(rev))


def archive_samples() -> list[str]:
    """Ревизии закрытия поставок — по одной на каталог в `delivery/archive/`.

    Берём коммит, ДОБАВИВШИЙ каталог (`--diff-filter=A`, последний в логе), в
    порядке от старых к новым. Число поставок — десятки, поэтому это дешёвле, чем
    обходить всю историю снимков.
    """
    if not ARCHIVE.is_dir():
        return []
    # Порядок берём из ИСТОРИИ, а не из времени коммита. Сортировка по `%ct`
    # разъезжается при совпадении секунды: в фикстуре все поставки попали в одну,
    # и началом окна оказалась САМАЯ НОВАЯ — проверка сравнивала «сейчас» с
    # «сейчас» и молчала. В настоящем репозитории это редкость, но оракул, чья
    # правильность зависит от скорости коммитов, оракулом не является.
    order = {rev: i for i, rev in enumerate(
        git("-C", str(ROOT), "rev-list", "--topo-order", "HEAD").split())}  # 0 = самый новый
    revs: list[str] = []
    for d in sorted(p for p in ARCHIVE.iterdir() if p.is_dir()):
        rel = f"delivery/archive/{d.name}"
        log = [l for l in git("-C", str(ROOT), "log", "--diff-filter=A",
                              "--format=%H", "--", rel)
               .split("\n") if l.strip()]
        if log:
            revs.append(log[-1].strip())
    # order даёт «насколько давно»: больший индекс = старше. Нужен возрастающий
    # возраст -> сортируем по убыванию индекса.
    return sorted(set(revs), key=lambda r: -order.get(r, 0))


def debt_is_not_frozen() -> list[str]:
    """Долг обязан таять, и у него не должно быть вечных жильцов.

    Три состояния, и проверка узнаёт их САМА, без разрешения от агента, — иначе
    получился бы гейт, который нельзя пройти в конфигурации, разрешённой каноном
    (тот же класс, что F4/F6/F13, и первое, что с ним сделают, — отключат):
      • долга нет (снимки пусты или их нет) -> проход;
      • данных мало (закрытых поставок меньше окна) -> проход + сколько накоплено;
      • накопилось -> судим.
    """
    now = debt_at("HEAD")
    if not now:
        return []  # долга нет — таять нечему, и это нормальное состояние
    samples = archive_samples()
    if len(samples) < DEBT_WINDOW:
        print(
            f"debt: накоплено {len(samples)} закрытых поставок из {DEBT_WINDOW} — "
            f"проверка тренда включится на {DEBT_WINDOW}-й "
            f"(сейчас в долге {len(now)} записей, вес {sum(now.values())})"
        )
        return []

    window = samples[-DEBT_WINDOW:]
    oldest = debt_at(window[0])
    if not oldest:
        return []  # на начале окна долга не было — мерить нечего

    errors: list[str] = []
    was, is_now = sum(oldest.values()), sum(now.values())
    if is_now >= was:
        errors.append(
            f"debt: за последние {DEBT_WINDOW} поставок долг не растаял "
            f"({was} -> {is_now}). Ратчет запрещает РОСТ и не требует таяния, "
            "поэтому неподвижный снимок проходит вечно — а значит правило "
            "«baseline тает» держится ни на чём. Почисти часть легаси в этой "
            "поставке либо назови причину в blockers и перенеси срок"
        )

    # Вечный жилец: запись, прожившая ВСЁ окно И НЕ СДВИНУВШАЯСЯ. Сумму можно
    # уронить, растопив лёгкие записи, а тяжёлые оставив гнить, — поэтому меряется
    # и возраст. Но «прожила окно» само по себе жильцом не делает: запись, которую
    # честно чистят по частям (40 -> 34 -> ... -> 10), тоже живёт всё окно, и
    # ругаться на неё — верный способ добиться того, чтобы проверку отключили.
    # Признак гниения — вес не уменьшился ни разу.
    samples_debt = [debt_at(r) for r in window]
    stuck = sorted(
        p for p in now
        if all(p in s for s in samples_debt) and now[p] >= samples_debt[0][p]
    )
    if stuck:
        errors.append(
            f"debt: {len(stuck)} записей живут все {DEBT_WINDOW} поставок подряд — "
            f"это уже не «известное нарушение», а вечный жилец: "
            + ", ".join(stuck[:5])
            + ("…" if len(stuck) > 5 else "")
        )
    return errors


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--require-spec", action="store_true")
    ap.add_argument("--require-verify", action="store_true")
    ap.add_argument(
        "--require-ci",
        action="store_true",
        help="fail unless ci-oracles: deployed (§10.4)",
    )
    ap.add_argument(
        "--diff-base",
        metavar="REF",
        help="check circuit breakers §3.4 against REF (e.g. origin/main)",
    )
    args = ap.parse_args()

    errors: list[str] = []
    warnings: list[str] = []

    if not (DELIVERY / "CONSTITUTION.md").is_file():
        errors.append("missing delivery/CONSTITUTION.md")
    if not ACTIVE.is_dir():
        errors.append("missing delivery/active/")
        for w in warnings:
            print(f"WARNING: {w}")
        for e in errors:
            print(f"ERROR: {e}", file=sys.stderr)
        print(f"delivery_check: {len(errors)} error(s), {len(warnings)} warning(s)")
        return 1

    status = read(ACTIVE / "STATUS.md")
    if not status:
        # Пустой active/ — ШТАТНОЕ состояние (§2.3a): предыдущая поставка
        # заархивирована, следующая не начата. Ошибкой это быть не может, иначе
        # контур красный между поставками — причём §13.1 сам загоняет проект в
        # это состояние, требуя архивации на handoff (полевая находка F12).
        # Проверки уровня архива ниже продолжают работать: именно в idle всплывает
        # просроченное наблюдение.
        warnings.append(
            "idle: нет delivery/active/STATUS.md — активной поставки нет (§2.3a). "
            "Начинаешь работу? Создай STATUS по шаблону A.2"
        )
    else:
        allowed = {
            "specify",
            "plan",
            "tasks",
            "implement",
            "verify",
            "converge",
            "handoff",
        }
        implement_like = {"implement", "verify", "converge", "handoff"}

        raw_phase = field(status, "phase")
        raw_class = field(status, "class")

        phase_m = (
            re.match(r"(?i)^([a-z_]+)", raw_phase)
            if not is_placeholder(raw_phase)
            else None
        )
        class_m = (
            re.match(r"(?i)^([SML])\b", raw_class)
            if not is_placeholder(raw_class)
            else None
        )
        phase = phase_m.group(1).lower() if phase_m else ""
        klass = class_m.group(1).upper() if class_m else ""

        if is_placeholder(raw_phase):
            errors.append(
                f"STATUS.md: phase not filled in (template placeholder {raw_phase!r})"
            )
        elif not phase:
            errors.append("STATUS.md: missing phase")
        elif phase not in allowed:
            # constitution is project-level file, not active phase
            errors.append(
                f"STATUS.md: unknown phase '{phase}' "
                f"(allowed: {', '.join(sorted(allowed))})"
            )

        if not klass:
            msg = (
                f"STATUS.md: class not resolved (value {raw_class!r}) — "
                "cannot apply §2.2 artifact gates; write exactly one of S|M|L"
            )
            # На specify класс ещё может уточняться; с plan и дальше это блокер:
            # неизвестный класс = молча отключённые требования spec/plan.
            if phase == "specify":
                warnings.append(msg)
            else:
                errors.append(msg)

        spec = ACTIVE / "spec.md"
        plan = ACTIVE / "plan.md"
        tasks = ACTIVE / "tasks.md"
        verify = ACTIVE / "verify-report.md"
        eval_smoke = ACTIVE / "eval-smoke.md"

        if klass in {"M", "L"} and phase in {
            "plan",
            "tasks",
            *implement_like,
        }:
            if not spec.is_file():
                errors.append(f"class {klass} at phase={phase}: missing active/spec.md")

        if klass in {"M", "L"} and phase in implement_like:
            if not plan.is_file():
                errors.append(f"class {klass} at phase={phase}: missing active/plan.md")
            if not tasks.is_file():
                errors.append(f"class {klass} at phase={phase}: missing active/tasks.md")
            # §3.3 называет это stop-gate'ом — значит error, не warning.
            # `deferred` (§2.2b) — законный третий вариант: человека нет, работа
            # идёт под запись долга. Он пускает до converge включительно, но НЕ на
            # handoff: подпись под ожиданиями обязательна там, где человек всё
            # равно есть — на мерже. Без этого значения агент без доступного
            # человека занижал класс до S, обходя требование спеки законным с виду
            # способом (найдено независимым развёртыванием).
            e, w = signature_verdict("human_ok_spec", field(status, "human_ok_spec"), klass, phase)
            errors += e
            warnings += w

        if klass == "L" and phase in implement_like:
            # §2.2b распространяется на ВСЕ поля-подписи, а не только на спеку:
            # `human_ok_plan` упирался в тот же тупик, и агент без человека выбирал
            # между «встать» и «занизить класс» — дыра, закрытая один раз, вернулась
            # во втором поле. Развилка теперь одна на класс полей (см. функцию).
            e, w = signature_verdict("human_ok_plan", field(status, "human_ok_plan"), klass, phase)
            errors += e
            warnings += w

        if klass == "S" and phase in implement_like and not tasks.is_file():
            errors.append("class S at implement+: missing active/tasks.md (mini-spec)")

        if not verify.is_file():
            if phase == "verify":
                # Фаза в процессе: отчёт ещё пишется — но выйти из неё без него нельзя.
                warnings.append(
                    "phase=verify: active/verify-report.md not created yet"
                )
            elif phase in {"converge", "handoff"}:
                errors.append(
                    f"phase={phase}: missing active/verify-report.md (DoD §3.2.2)"
                )

        if klass in {"M", "L"} and phase in {"verify", "converge", "handoff"}:
            if not eval_smoke.is_file():
                errors.append(
                    "class M/L at verify+: missing active/eval-smoke.md "
                    "(product oracles are mandatory, §6.2)"
                )

        # --- §12.5: маячок на рисковый дифф. Предупреждение на verify, ОТКАЗ на
        # handoff — та же лестница, что у `deferred` (§2.2b): работать не мешаем,
        # объявить сделанным не даём. Блокировать на каждом коммите нельзя: правка
        # опечатки получала бы требование ревью, и маячок сняли бы через неделю.
        if phase in {"verify", "converge", "handoff"}:
            rbase = args.diff_base or "HEAD~1"
            rstats = diff_stats(rbase)
            if rstats and rstats[4]:
                gaps = risk_review_gaps(
                    read(verify),
                    risky_classes(rstats[4], rbase),
                    diff_identifiers(rstats[4]),
                )
                for g in gaps:
                    (errors if phase == "handoff" else warnings).append(
                        f"рисковый дифф: {g}"
                    )

        # --- Долг не должен болтаться вечно (§3.5). Проверяется ТОЛЬКО на handoff:
        # на каждом коммите это блокировало бы работу, не связанную со старым
        # долгом, и такой гейт отключают через неделю. Работать не мешаем —
        # не даём объявить сделанным.
        if phase == "handoff":
            errors.extend(debt_is_not_frozen())

        # --- §13.1: поставка уходит в archive вместе с обязательством проверить
        # её в проде. Без этих полей «готово» проверено во всех средах, кроме
        # единственной значимой.
        if phase == "handoff":
            sig = field(status, "observe_signal")
            until = field(status, "observe_until")
            if is_placeholder(sig):
                errors.append(
                    "phase=handoff: пусто observe_signal (§13.2) — что именно "
                    "будет проверено в проде; «ошибок нет» сигналом не является, "
                    "молчание одинаково выглядит и при не вызываемом коде"
                )
            if is_placeholder(until):
                errors.append(
                    "phase=handoff: пусто observe_until (§13.1) — до какой даты "
                    "наблюдаем; обязательство без срока не выполняется"
                )
            # Уровень наблюдаемости — значение проверяемое, а не декларативное
            # (урок §10.4: самозаявленное `ci-oracles: tooling` при красном CI).
            level = field(status, "observability")
            if not is_placeholder(level) and level.strip().startswith(("2", "3")):
                # Цифра, которой НЕ предшествует латинская буква: так число порога
                # (`180мс`) отличается от id примера (`A1`) и от имени метрики
                # (`p95`). Наивный поиск любой цифры проходил на сигнале
                # «A1 подтверждён, ошибок нет» — то есть по неверной причине.
                if not re.search(r"(?<![A-Za-z])\d", sig):
                    errors.append(
                        f"observability: {level.strip()} заявлен, но observe_signal "
                        "без метрики с числом (§13.3) — уровень 2+ означает замер "
                        "ДО и порог, а не «мониторинг вроде подключён»"
                    )

        if phase == "handoff" and verify.is_file():
            vr = read(verify)
            if not re.search(r"READY FOR HANDOFF", vr, re.I):
                errors.append(
                    "phase=handoff: verify-report.md lacks 'READY FOR HANDOFF' verdict"
                )
            # §9.2: метрики снимаются на handoff. Без гейта ритуал не выполняется.
            if "Harness metrics" not in vr:
                errors.append(
                    "phase=handoff: verify-report.md lacks the 'Harness metrics' "
                    "block (§9.2 / A.10) — run: python scripts/delivery_metrics.py "
                    "--base origin/main --write"
                )

        # --- Builder ≠ Verifier (§5.2): не сама независимость, но явное заявление
        # о ней. Настоящее разделение обеспечивает required review в branch
        # protection (CQG §8.5); здесь ловим «сам построил, сам принял».
        if phase in {"verify", "converge", "handoff"} and verify.is_file():
            declared = field(read(verify), "Verifier") or field(status, "verifier")
            builder = field(status, "builder")
            if is_placeholder(declared):
                errors.append(
                    "verify-report.md: Verifier not filled in — Builder must not "
                    "accept own work (§5.2); write process:ci | agent:NAME | human:NAME"
                )
            elif (
                klass in {"M", "L"}
                and not is_placeholder(builder)
                and declared.strip().lower() == builder.strip().lower()
            ):
                errors.append(
                    f"class {klass}: verifier == builder ('{declared}') — §5.2 "
                    "requires a different agent/model/human, or process:ci"
                )

        # --- §3.1d уровень 3 / DoD §3.2.7: ревью утверждений пропорционально
        # непроверяемой части. `n/a` законен, только если КАЖДОЕ утверждение
        # ведёт к примеру, который человек подписал до кода; иначе ожидание
        # придумал исполнитель, и подпись обязана быть.
        if klass in {"M", "L"} and phase in {"verify", "converge", "handoff"} and verify.is_file():
            vr = read(verify)
            reviewed = field(vr, "asserts_reviewed_by")
            digest = re.search(r"(?im)^\s*asserts_without_example:\s*(\d+)\s*$", vr)
            if is_placeholder(reviewed):
                errors.append(
                    f"class {klass}: verify-report.md без asserts_reviewed_by "
                    "(§3.1d уровень 3, DoD §3.2.7) — последний рубеж против "
                    "неверного ожидания; вставь дайджест: "
                    "bash scripts/lint/assert_digest.sh >> verify-report.md"
                )
            elif reviewed.lower().startswith("n/a"):
                if not digest:
                    errors.append(
                        "asserts_reviewed_by: n/a без вставленного дайджеста "
                        "(нет строки 'asserts_without_example: N') — n/a надо "
                        "заслужить, а не заявить (§3.1d уровень 3)"
                    )
                elif int(digest.group(1)) > 0:
                    errors.append(
                        f"asserts_reviewed_by: n/a, но {digest.group(1)} "
                        "утверждений не ссылаются на примеры спеки — их ожидание "
                        "придумал исполнитель; нужна подпись human:… at=… "
                        "(§3.1d уровень 3)"
                    )
            else:
                # Третье появление той же дыры. §2.2b закрыла её для `human_ok_spec`,
                # v1.30 — для `human_ok_plan`, и оба раза правка была на ПОЛЕ, а не на
                # класс полей: здесь ветка принимала ЛЮБУЮ непустую строку, поэтому
                # `asserts_reviewed_by: посмотрел сам` и `by=agent:…` проходили, а
                # автономному агенту не оставалось законного значения вовсе. Теперь
                # поле идёт через ту же развилку: подпись человека, либо `deferred`
                # с причиной, либо заслуженное `n/a` выше.
                e, w = signature_verdict("asserts_reviewed_by", reviewed, klass, phase)
                errors += e
                warnings += w

        # --- §3.1d уровень 1: ожидание обязано появиться РАНЬШЕ кода.
        # Проверяем не качество примеров (это невозможно), а сам факт, что они
        # есть и на них ссылаются тесты: иначе ожидание придумал тот же, кто писал
        # код, и все гейты ниже проверяют его согласие с самим собой.
        if klass in {"M", "L"} and phase in implement_like and spec.is_file():
            spec_text = read(spec)
            ex_ids = re.findall(r"(?m)^\s*\|\s*([A-Z]\d+)\s*\|", spec_text)

            # Корпус «где искать ссылки»: smoke + tasks + verify + тексты тестов.
            # Строится БЕЗУСЛОВНО, потому что его читают ДВЕ независимые проверки —
            # ссылки на id ниже и реляционный оракул §6.5 дальше.
            #
            # lab-12: он строился внутри else-ветки, и обе ветки с ошибкой роняли
            # гейт `UnboundLocalError: haystack` ВМЕСТО того, чтобы напечатать уже
            # сформулированный диагноз. Класс: **проверка, обязанная поставить
            # диагноз, умирает вместо диагноза** — исполнитель видит поломку
            # инструмента там, где ему сообщали о его собственной ошибке. Это
            # зеркало «гейта, врущего зелёным»: тот молчит, когда должен говорить,
            # этот кричит не о том. Мера — не «инициализировать переменную», а
            # держать сбор данных отдельно от разбора причин.
            haystack = read(eval_smoke) + read(tasks) + read(verify)
            for root_dir in ("tests", "backend/tests", "src/tests"):
                d = ACTIVE.parent.parent / root_dir
                if not d.is_dir():
                    continue
                for f in d.rglob("*test*"):
                    # Только текстовые исходники и не служебные каталоги:
                    # маска ловила .pyc и роняла гейт (F9).
                    if (
                        f.is_file()
                        and f.suffix in TEST_TEXT_SUFFIXES
                        and not any(p in SKIP_DIR_PARTS for p in f.parts)
                    ):
                        haystack += read(f)

            if not re.search(r"(?im)^#+\s*acceptance\s+examples", spec_text):
                errors.append(
                    f"class {klass}: spec.md без блока '## Acceptance examples' "
                    "(§3.1d) — конкретные вход→выход, подтверждённые человеком "
                    "ДО кода; проза «работает корректно» подписью не является"
                )
            elif not ex_ids:
                # Грамматика id названа ЯВНО: она не очевидна, а её нарушение
                # раньше выглядело как «примеров нет» при полной таблице примеров.
                # lab-12: арка написала id вида `EX1` и получила краш; вторая арка
                # переименовала свои id, обходя соседнюю проблему, — то есть
                # неназванное правило заставляло подстраиваться вслепую.
                errors.append(
                    "spec.md: блок Acceptance examples есть, но примеров с id в "
                    "нём нет (§3.1d). id читается из первой колонки таблицы и "
                    "обязан быть вида ОДНА заглавная латинская буква + цифры "
                    "(`A1`, `E2`); `EX1`, `A.1`, `1` и `случай-1` не считаются"
                )
            else:
                # id должны встречаться в тестах или eval-smoke: связь примера с
                # проверкой — то, что отличает обещание от отчёта о реализации.
                missing = [i for i in dict.fromkeys(ex_ids) if i not in haystack]
                if missing:
                    warnings.append(
                        "acceptance-примеры без ссылки в тестах/eval-smoke: "
                        f"{', '.join(missing)} (§3.1d) — пометь тест id примера"
                    )

                # Порядок «пример раньше теста» — на verify и дальше: раньше
                # тестов может просто не быть, и проверка ругалась бы на штатное
                # состояние фазы implement.
                if phase in {"verify", "converge", "handoff"}:
                    test_dirs = [d for d in ("tests", "backend/tests", "src/tests")
                                 if (ACTIVE.parent.parent / d).is_dir()]
                    warnings += expectation_predates_tests(ex_ids, test_dirs)

            # --- §6.5 уровень 2: хотя бы один реляционный оракул на M/L.
            # «Минимум один» стояло в §6.5 практикой и не принуждалось ничем —
            # та же форма, что F7. Пример со значением (`f(2) == 4`) закрепляет
            # баг, если ожидание списано с кода, и мутационный гейт его не поймает:
            # мутант будет честно убит НЕВЕРНЫМ утверждением. Свойство подделать
            # нельзя, потому что ожидаемого значения в нём нет.
            #
            # ⚠ Это проверка НАЛИЧИЯ, и она заполняется галочкой: `@given(...)` с
            # `assert True` её проходит. Ловит такое не она, а мутационный гейт —
            # декоративное свойство оставляет мутантов живыми. Поэтому требование
            # осмысленно ТОЛЬКО при работающем mutation (на macOS —
            # `brew install coreutils`, CQG §5 шаг 3), и об этом сказано в тексте
            # ошибки: иначе получим ритуал вместо оракула.
            if not re.search(r"@given|@hypothesis\.given|fc\.assert|fc\.property",
                             haystack):
                warnings.append(
                    f"class {klass}: ни одного реляционного оракула (§6.5) — "
                    "не найдено ни `@given` (hypothesis), ни `fc.property` "
                    "(fast-check). Инвариант, round-trip, идемпотентность, "
                    "метаморфное отношение или differential: в них нет ожидаемого "
                    "значения, поэтому в них нельзя спрятать неверное ожидание. "
                    "Один инвариант обычно ловит больше десяти тестов-значений, "
                    "потому что раннер перебирает входы, о которых автор не думал. "
                    "Проверь заодно, что mutation-гейт у тебя не пропускается: "
                    "иначе слабое свойство (`assert result is not None`) пройдёт"
                )

        # kind/behavior читаем один раз — их используют обе проверки ниже.
        kind = field(status, "kind").lower()
        behavior = field(status, "behavior-oracles").lower()

        # --- §3.1c: багфикс обязан принести тест, который падал до фикса
        if kind.startswith("bugfix") and phase in {"verify", "converge", "handoff"}:
            repro = field(status, "repro_test")
            if is_placeholder(repro):
                errors.append(
                    "kind=bugfix at verify+: missing repro_test (§3.1c) — тест, "
                    "который падал до фикса; иначе баг вернётся"
                )
            elif repro.lower().startswith("n/a") and "reason=" not in repro.lower():
                errors.append(
                    "repro_test: n/a без reason= (§3.1c) — «не воспроизводится» "
                    "обычно значит «не пробовал»"
                )

        # --- §12.1: багфикс обязан показать, КАК искали, а не только что нашёл.
        # repro_test доказывает, что баг найден; журнал гипотез — что его не будут
        # искать заново с нуля.
        if kind.startswith(("bugfix", "hotfix")) and phase in {
            "verify",
            "converge",
            "handoff",
        }:
            diag = field(status, "diagnosis")
            diag_file = ACTIVE / "diagnosis.md"
            if is_placeholder(diag):
                errors.append(
                    f"kind={kind.split()[0]} at verify+: missing diagnosis (§12.1) "
                    "— журнал гипотез с вердиктами; n/a только с reason="
                )
            elif diag.lower().startswith("n/a"):
                if "reason=" not in diag.lower():
                    errors.append(
                        "diagnosis: n/a без reason= (§12.1) — «нашёл сразу» и «не "
                        "искал» обязаны различаться в тексте, а не в тишине"
                    )
            elif not diag_file.is_file():
                errors.append(
                    "diagnosis указывает на файл, которого нет (§12.1) — "
                    "ожидается delivery/active/diagnosis.md"
                )
            elif not verdict_blocks(read(diag_file)):
                errors.append(
                    "diagnosis.md без заполненных вердиктов (§12.1) — гипотезы без "
                    "ОПРОВЕРГНУТА/ПОДТВЕРЖДЕНА это список подозрений: следующий "
                    "читатель обязан перепроверить всё заново. Ожидается вердикт "
                    "внутри СТРУКТУРНОГО блока: пункт списка, строка таблицы или "
                    "раздел (перенос строки внутри пункта допустим). Строки шаблона "
                    "(с <…>) и проза о формате вердиктами не считаются"
                )

        # --- §12.3: остановка обязана быть оформлена, иначе восстановление
        # контекста перекладывается на человека — то самое время, которое контур
        # экономит.
        blockers = field(status, "blockers")
        if blockers and not is_placeholder(blockers) and blockers.lower() not in {
            "none",
            "нет",
            "n/a",
        }:
            esc = ACTIVE / "escalation.md"
            if not esc.is_file():
                errors.append(
                    f"blockers непусты ({blockers[:50]}), а active/escalation.md "
                    "нет (§12.3) — «я застрял» решением не является: нужны что "
                    "пробовал, какой нужен ответ, два варианта с ценой"
                )
            else:
                # Строки шаблона не считаются: скопированный и незаполненный
                # escalation.md — это не оформленная остановка (ср. STATUS, v1.5).
                lines_e = [ln for ln in read(esc).splitlines() if not unfilled(ln)]
                # Разметка принимается ЛЮБАЯ разумная: жирная строка шаблона,
                # markdown-заголовок, list-item, строка таблицы. До delivery@1.39
                # принималась только жирная строка, и `## Вариант 1 — …` давало
                # «вариантов 0» — то есть диагноз про СОДЕРЖАНИЕ, когда причина
                # была в ФОРМЕ. На dogfooding'е (lab-10) я споткнулся об это трижды
                # в трёх артефактах; ни одна подстройка не была про смысл.
                opts = len(
                    [
                        ln
                        for ln in lines_e
                        if re.match(
                            # `\s+` обязателен: с `\s*` заголовок раздела
                            # «## Варианты» считался вариантом («вариант» + «ы»),
                            # и одного варианта хватало на два. Поймал существующий
                            # тест, а не я.
                            r"(?i)^\s*(?:#{1,6}\s*|[-*]\s+|\|\s*)?\**\s*"
                            r"(?:вариант|option)\s+\w",
                            ln,
                        )
                    ]
                )
                costs = len(
                    [ln for ln in lines_e if re.search(r"(?i)\bцена\b|\bcost\b", ln)]
                )
                if opts < 2:
                    errors.append(
                        f"escalation.md: заполненных вариантов {opts}, нужно ≥2 "
                        "(§12.3) — один вариант это просьба согласиться, а не выбор; "
                        "второй всегда есть и называется «не делать / отложить». "
                        "Ожидается строка, начинающаяся со слова «Вариант» (можно "
                        "как заголовок `## Вариант A`, жирным `**Вариант A:**`, "
                        "пунктом списка или строкой таблицы)"
                    )
                elif costs < 2:
                    errors.append(
                        f"escalation.md: вариантов {opts}, а названных цен {costs} "
                        "(§12.3) — вариант без цены выбрать нельзя"
                    )

        # --- §12.2a: отклонённые варианты. Без следа тот же тупик предлагают
        # снова — и он снова выглядит разумным, потому что причина отказа нигде
        # не записана.
        if klass in {"M", "L"} and phase in implement_like and plan.is_file():
            plan_text = read(plan)
            sec = re.search(
                r"(?ims)^#{2,3}\s*rejected\s+alternatives\s*$(.*?)(?=^#{2,3}\s|\Z)",
                plan_text,
            )
            msg_alt = ""
            if not sec:
                msg_alt = (
                    "plan.md без секции '## Rejected alternatives' (§12.2a) — "
                    "отброшенный подход без записанной причины предлагается снова"
                )
            else:
                # Та же склейка переносов, что у журналов: причина часто уезжает на
                # вторую строку, и построчный разбор объявлял запись «без причины».
                entries = [
                    ln
                    for ln in list_entries(sec.group(1))
                    if not unfilled(ln)
                    and re.search(r"(?i)потому что|because|reason=", ln)
                ]
                if not entries:
                    msg_alt = (
                        "plan.md: 'Rejected alternatives' без заполненных записей "
                        "с причиной (§12.2a) — законна и запись «рассматривали "
                        "только X, потому что Y исключён требованием Z»"
                    )
            if msg_alt:
                (errors if klass == "L" else warnings).append(msg_alt)

        # --- §12.2: журнал решений. Проверяется ФОРМАТ: лента без альтернатив
        # неаудируема, а именно аудируемость — весь смысл файла.
        dec_file = ACTIVE / "decisions.md"
        late = phase in {"verify", "converge", "handoff"}
        if dec_file.is_file():
            good, bad = decision_lines(read(dec_file))
            if bad:
                errors.append(
                    f"decisions.md: {len(bad)} строк(а) не в формате §12.2 "
                    "«выбрал X вместо Y — потому что Z»: "
                    + "; ".join(b[:55] for b in bad[:3])
                )
            if klass == "L" and late and not good:
                errors.append(
                    "class L: decisions.md без ни одного решения (§12.2) — эпик "
                    "или новый модуль без выбора не бывает"
                )
            # Цена, а не предпочтение: «потому что дешевле» неопровержимо, значит
            # аудита не даёт, ради которого файл и ведётся (§12.2a).
            # Идентификаторы диффа — то, с чем сверяется «цена». Диффа нет
            # (нет ref'а, не git) -> `None`, и проверка молчит: предупреждение по
            # неверной причине учит игнорировать гейт.
            # Без `--diff-base` берём `HEAD~1`: иначе проверка молчала бы на
            # каждом локальном прогоне, а в CI работала — то есть вела бы себя
            # по-разному там, где решение и принимается.
            dec_stats = diff_stats(args.diff_base or "HEAD~1")
            diff_ids = diff_identifiers(dec_stats[4]) if dec_stats else None
            no_cost = decisions_without_cost(read(dec_file), diff_ids)
            if no_cost and late:
                warnings.append(
                    f"decisions.md: {len(no_cost)} решен(ий) без цены — причина не "
                    "названа ни числом, ни ссылкой в изменённый код: "
                    + "; ".join(n[:55] for n in no_cost[:3])
                    + ". «Дешевле» и «проще» проверить нельзя ничем; назови число "
                    "или процитируй то, что менял (файл, функцию, поле) — такое "
                    "не напишешь, не открыв дифф (§12.2a)"
                )
        elif klass == "L" and late:
            errors.append(
                "class L at verify+: missing active/decisions.md (§12.2)"
            )
        elif klass == "M" and late:
            warnings.append(
                "class M at verify+: нет active/decisions.md (§12.2) — поведение "
                "агента неаудируемо без чтения всего диффа"
            )

        # --- §3.1b: рефакторинг без behavior-oracles = тихая регрессия
        if kind.startswith("refactor") and phase in {"verify", "converge", "handoff"}:
            covered = (
                not behavior.startswith("weak")
                or "characteriz" in status.lower()
                or "характеризац" in status.lower()
                or "refactor" in field(status, "waivers").lower()
            )
            if not covered:
                errors.append(
                    "kind=refactor with behavior-oracles: weak — «компилируется» не "
                    "доказывает сохранение поведения (§3.1b). Нужны характеризационные "
                    "тесты, наблюдаемая проверка или human waiver со словом refactor"
                )

        # --- CI (§10.4): единственный слой, который агент не может обойти локально
        ci = field(status, "ci-oracles").lower()
        waivers = field(status, "waivers").lower()
        if is_placeholder(ci):
            warnings.append(
                "STATUS.md: missing ci-oracles (weak|tooling|deployed) — §10.4"
            )
        elif ci.startswith("weak"):
            # Было `"ci" not in waivers`: строка `waivers: ci` снимала требование
            # ПОДСТРОКОЙ — без причины и без подписи. Форма waiver'а одна на весь
            # контур (§4.3a). Нашло приёмочное развёртывание.
            ci_waived = bool(re.search(r"ci\b.*reason=.*by=human:", waivers))
            # Компенсация §10.4 правило 4 — ТРЕТИЙ законный выход, наравне с waiver'ом.
            # Она была описана прозой и не проверялась ничем, поэтому автономное
            # развёртывание в проект без хостинга не имело **честного** способа сделать
            # гейт зелёным: waiver требует человека, занижать класс запрещено §2.2b, а
            # `blockers:` + `escalation.md` гейт не принимал. Рядом лежали две дешёвые
            # лазейки (занизить класс, написать `waivers: ci`), то есть канон учил
            # обходить себя законным с виду способом — ровно то, против чего §2.2b.
            # Асимметрия была видна в собственном выводе: для `human_ok_*` третье
            # значение сделали, для `ci-oracles` — нет.
            #
            # Компенсация проверяется по ФАКТУ артефакта, а не по заявлению: строка
            # `clean_clone_run:` в verify-report (что прогнали и когда) + непустые
            # `blockers:` + существующий `escalation.md` (§12.3 сам требует там два
            # варианта с ценой). Это не эквивалент CI и не снятие требования: остаётся
            # громкий warning, `ci-oracles` остаётся `weak`, и строка приёмки §6
            # закрывается как `weak`, а не как `auto`.
            compensated = (
                bool(re.search(r"(?im)^\s*\**clean_clone_run\**\s*:\s*\S", read(verify)))
                and bool(field(status, "blockers").lower() not in {"", "none", "-"})
                and (ACTIVE / "escalation.md").is_file()
            )
            if klass == "L" and not ci_waived and not compensated:
                errors.append(
                    "class L with ci-oracles: weak — нужен либо human waiver "
                    "(`waivers: ci reason=… by=human:…`), либо компенсация §10.4 п.4: "
                    "строка `clean_clone_run: <что прогнал> at=<дата>` в "
                    "verify-report.md + непустые blockers: + active/escalation.md. "
                    "Занижать класс, чтобы гейт позеленел, запрещено (§2.2b)"
                )
            elif klass == "L" and compensated and not ci_waived:
                warnings.append(
                    "class L, ci-oracles: weak — закрыто компенсацией §10.4 п.4 "
                    "(clean_clone_run + blockers + escalation.md). Это НЕ эквивалент "
                    "CI: строка приёмки §6 закрывается как weak, не как auto"
                )
            else:
                warnings.append(
                    "ci-oracles: weak — local gates are bypassable (§10.4); "
                    "Verifier must attach a clean-clone run to verify-report.md"
                )
        # 'tooling' — легитимный режим (гейт мержа в репо, серверного нет по тарифу),
        # а не поддавки: см. §10.4. Недопустим только 'weak'.
        if args.require_ci and not ci.startswith(("deployed", "tooling")):
            errors.append(
                "--require-ci: ci-oracles is neither 'deployed' nor 'tooling'"
            )

        stack = field(status, "stack")
        if is_placeholder(stack) or "delivery@" not in stack:
            warnings.append(
                "STATUS.md: missing stack version "
                "(e.g. 'delivery@<version>, cqg@<version>, okf@absent')"
            )

        # --- Circuit breakers (§3.4): анти-oneshot по объёму поставки.
        #
        # `kind: bootstrap` breaker'ом не мерится, и это не поддавки. Bootstrap — не
        # поставка продукта: у него своя DoD (§7.3), он по построению трогает всё
        # дерево контура и не может быть «разрезан на части» — совет гейта «split the
        # PR» для него не выполним ни в каком виде. Приёмочное развёртывание показало
        # это числом: даже после исключения механики контура остаётся 30 файлов и
        # 2437 строк конфигов, снимков и workflow'ов против лимита 800. Единственным
        # выходом оставался рутинный waiver, который §4.3a сам называет
        # обесцениванием механизма — то есть гейт учил себя обходить.
        #
        # Объём при этом не замалчивается: он печатается строкой ниже, и §7.3 требует
        # приёмку §6 — bootstrap проверяется своей процедурой, а не breaker'ом.
        if field(status, "kind").lower().startswith("bootstrap"):
            print(
                "breakers: kind=bootstrap — объём не мерится (§3.4): развёртывание "
                "контура не режется на части, его DoD — §7.3 + приёмка §6"
            )
        elif args.diff_base:
            limits = dict(DEFAULT_BREAKERS)
            # Одна и та же форма покрывает и override в circuit_breakers,
            # и human waiver: "max_files_touched=40 reason=… by=human:…".
            for m in re.finditer(r"(max_[a-z_]+)[ \t]*=[ \t]*(\d+)", status):
                if m.group(1) not in limits:
                    continue
                # Смотрим СТРОКУ, в которой стоит override, а не только совпадение.
                # §3.4 различает две вещи одной формы: настройка проекта (строка
                # `circuit_breakers:`) и **human waiver**. Про waiver канон говорил
                # «только человек», а парсер принимал `max_loc_diff=99999` без
                # причины и без подписи — то есть требование жило в прозе, а
                # механика позволяла агенту поднять себе лимит молча. Три
                # независимых развёртывания нашли это по отдельности.
                bol = status.rfind("\n", 0, m.start()) + 1
                eol = status.find("\n", m.end())
                line = status[bol: eol if eol != -1 else len(status)]
                if "circuit_breakers" in line.lower():
                    limits[m.group(1)] = int(m.group(2))
                    continue
                if "reason=" not in line or "by=human:" not in line:
                    errors.append(
                        f"waiver {m.group(1)}={m.group(2)} без reason= и by=human: "
                        "(§3.4) — лимит поднимает человек, не исполнитель. Нет "
                        "человека — не waiver, а `blockers:` + escalation.md (§12.3) "
                        "или более узкая поставка; настройка проекта пишется строкой "
                        "circuit_breakers:"
                    )
                    continue
                limits[m.group(1)] = int(m.group(2))
            stats = diff_stats(args.diff_base)
            if stats is None:
                warnings.append(
                    f"circuit breakers: ref '{args.diff_base}' unavailable "
                    "(shallow clone? need full history)"
                )
            else:
                n_files, added, deleted, excluded, changed = stats
                # --- §2.2a: уроки по затронутым путям должны быть упомянуты.
                # Warning, не error: сопоставление «префикс пути → урок»
                # приблизительно, а по §4.3b ложное срабатывание дороже пропуска.
                lessons = applicable_lessons(read(ARCHIVE / "INDEX.md"), changed)
                if lessons:
                    cited = read(plan) + read(tasks) + status
                    unread = [
                        i for i in lessons if not re.search(rf"\b{i}\b", cited)
                    ]
                    if unread:
                        warnings.append(
                            "archive/INDEX.md: уроки по затронутым путям не "
                            f"упомянуты: {', '.join(unread)} (§2.2a) — прочти "
                            "строки и сошлись на id в plan.md/tasks.md либо "
                            "напиши, почему не применимо"
                        )
                net = abs(added - deleted)
                print(
                    f"breakers: files={n_files} net_loc={net} (+{added}/-{deleted}), "
                    f"excluded={excluded} ({'|'.join(BREAKER_EXCLUDE)}), "
                    f"limits={limits}"
                )
                # --- Стартовый дифф (lab-11 F12/F13/F8). На specify/plan/tasks
                # поставка ещё не написала продуктового кода: всё, что дифф
                # показывает сверх BREAKER_EXCLUDE, принесено извне — незамерженная
                # предыдущая поставка (bootstrap, который мержится ПОКА активен,
                # §7.2 шаг 6) или ветка от старой базы после squash-мержа. Обе арки
                # lab-11 обнаружили это на handoff ценой полного цикла: breaker
                # мерил 33 файла при собственных 2, и совет «split the PR» резал
                # нечего. Здесь тот же тупик называется на входе и стоит минуту.
                if phase in ("specify", "plan", "tasks") and n_files:
                    # Слито в локальный main, но не запушено — отдельный честный
                    # диагноз: чинится push'ем, а не rebase'ом.
                    alt_clean = False
                    for cand in ("main", "master"):
                        alt = None if cand == args.diff_base else diff_stats(cand)
                        if alt is not None and alt[0] == 0:
                            alt_clean = True
                            break
                    if alt_clean:
                        warnings.append(
                            f"стартовый дифф против {args.diff_base} непуст "
                            f"({n_files} файл(ов)), против локального main пуст: "
                            "предыдущая поставка слита, но не запушена — CI и "
                            "breakers меряют чужой дифф, пока push не ушёл (§3.4)"
                        )
                    else:
                        errors.append(
                            f"стартовый дифф непуст: {n_files} файл(ов) кода в "
                            f"{args.diff_base}..HEAD уже на фазе {phase} — это "
                            "чужие изменения, поставка не стартует поверх них "
                            "(§7.2 шаг 6). Незамерженная предыдущая — слей через "
                            "merge_guard (bootstrap мержится ПОКА активен); ветка "
                            "от старой базы после squash-мержа — git rebase --onto "
                            f"{args.diff_base} <старая-база> (lab-11 F12/F8)"
                        )
                # §2.2b: класс S при S-нетипичном объёме — warning, не ошибка.
                # Большой механический багфикс бывает, но и занижение класса ради
                # обхода human_ok_spec выглядит именно так. Молчать нельзя:
                # молчание эту дыру и создало.
                if klass == "S" and (n_files > 5 or net > 200):
                    warnings.append(
                        f"class S, а тронуто {n_files} файл(ов) / {net} строк — "
                        "класс занижен? (§2.2b) Класс определяется работой, а не "
                        "доступностью человека; нет человека — human_ok_spec: deferred"
                    )
                if n_files > limits["max_files_touched"]:
                    errors.append(
                        f"circuit breaker: files_touched {n_files} > "
                        f"{limits['max_files_touched']} — split the PR or add a "
                        "human waiver line to STATUS (§3.4)"
                    )
                if net > limits["max_loc_diff"]:
                    errors.append(
                        f"circuit breaker: net loc_diff {net} > "
                        f"{limits['max_loc_diff']} — split the PR or add a "
                        "human waiver line to STATUS (§3.4)"
                    )

    # --- §2.2a: архив без индекса не читается, а отставший индекс врёт о полноте.
    # Обе проверки не зависят от фазы и от наличия diff-base: они про сам архив.
    if ARCHIVE.is_dir():
        shipments = sorted(d.name for d in ARCHIVE.iterdir() if d.is_dir())
        idx_text = read(ARCHIVE / "INDEX.md")
        if shipments and not idx_text:
            errors.append(
                f"delivery/archive/ содержит {len(shipments)} поставок, а "
                "INDEX.md нет (§2.2a / A.13) — неиндексированный архив никем "
                "не читается"
            )
        elif idx_text:
            unlisted = [s for s in shipments if s not in idx_text]
            if unlisted:
                errors.append(
                    "archive/INDEX.md отстал от архива: не упомянуты "
                    f"{', '.join(unlisted)} (§2.2a) — индекс, который врёт о "
                    "своей полноте, хуже отсутствующего"
                )

        # --- §13.1: просроченное наблюдение. Лаг в одну поставку — проверка
        # срабатывает тогда, когда человек всё равно смотрит в PR. Дыра названа
        # в каноне: если следующей поставки не будет, никто не проверит; на это
        # тот же периодический прогон, что okf_sync_gate --check-stale.
        today = date.today().isoformat()
        for name in shipments:
            arch_status = read(ARCHIVE / name / "STATUS.md")
            if not arch_status:
                continue
            until = field(arch_status, "observe_until")
            if is_placeholder(until):
                continue
            due = re.match(r"(\d{4}-\d{2}-\d{2})", until)
            if not due or due.group(1) > today:
                continue
            if not (ARCHIVE / name / "observed.md").is_file():
                errors.append(
                    f"наблюдение просрочено: {name} — observe_until={due.group(1)} "
                    f"(сегодня {today}), а observed.md нет (§13.1 / A.17). "
                    "Проверь сигнал в проде и закрой наблюдение, либо сдвинь срок "
                    "с причиной"
                )

    if args.require_spec and not (ACTIVE / "spec.md").is_file():
        errors.append("--require-spec: active/spec.md missing")
    if args.require_verify and not (ACTIVE / "verify-report.md").is_file():
        errors.append("--require-verify: verify-report.md missing")

    # --- §4.5: права на действия. Объявлено (CONSTITUTION) ↔ подключено (настройки).
    settings_path = ROOT / ".claude" / "settings.json"
    declared = permission_block(read(DELIVERY / "CONSTITUTION.md"))
    settings, s_err = read_json(settings_path)
    if s_err:
        errors.append(
            f".claude/settings.json: не парсится ({s_err}) — права агента "
            "не проверяемы (§4.5)"
        )
    perms = settings.get("permissions") or {}
    wired = {k: list(perms.get(k) or []) for k in ("deny", "ask")}

    if declared is None:
        msg = (
            "CONSTITUTION.md: нет блока `agent-permissions` (§4.5 / A.1) — контур "
            "контролирует выход и молчит про действия агента"
        )
        if any(wired.values()):
            errors.append(
                msg + "; при этом deny/ask в настройках заданы, то есть границы "
                "действий живут без ревью"
            )
        else:
            warnings.append(msg)
    elif not settings_path.is_file():
        errors.append(
            "CONSTITUTION.md объявляет agent-permissions, а .claude/settings.json "
            "нет (§4.5) — объявленный неработающий запрет хуже отсутствующего: "
            "он выглядит как контроль"
        )
    elif not s_err:
        for bucket in ("deny", "ask"):
            only_canon = [r for r in declared[bucket] if r not in wired[bucket]]
            only_wired = [r for r in wired[bucket] if r not in declared[bucket]]
            if only_canon:
                errors.append(
                    f"permissions.{bucket}: объявлено в CONSTITUTION, нет в "
                    f".claude/settings.json: {', '.join(only_canon)} (§4.5)"
                )
            if only_wired:
                errors.append(
                    f"permissions.{bucket}: есть в .claude/settings.json, нет в "
                    f"CONSTITUTION: {', '.join(only_wired)} (§4.5) — границу "
                    "действий двигали молча"
                )

    # --- §4.6: перевод из HITL в автономию обязан назвать существующий оракул.
    # Объявленная песочница без скрипта — снятая проверка с видом усиления;
    # класс тот же, что «скрипт лежал в репозитории, никто не вызывал» (§3.1a).
    for line in (declared or {}).get("sandbox", []):
        m_or = re.search(r"oracle=([^\s]+)", line)
        if not m_or:
            errors.append(
                f"sandbox без oracle=: {line[:60]} (§4.6) — перевод из HITL "
                "в автономию обязан назвать оракул, заменивший человека"
            )
        elif not (ROOT / m_or.group(1)).exists():
            errors.append(
                f"sandbox: oracle={m_or.group(1)} не существует (§4.6) — "
                "объявленная песочница без скрипта это снятая проверка "
                "с видом усиления"
            )

    # Ратчет прав: длинный allow при пустом deny = права росли только вверх.
    # Считаем и локальные настройки — именно там оседают клики «yes».
    local, _ = read_json(ROOT / ".claude" / "settings.local.json")
    n_allow = len(perms.get("allow") or []) + len(
        (local.get("permissions") or {}).get("allow") or []
    )
    if n_allow >= 50 and not wired["deny"]:
        warnings.append(
            f"permissions: {n_allow} правил в allow и ни одного в deny (§4.5) — "
            "права накапливались кликами «yes» и ни разу не сужались"
        )

    if (ROOT / "CODE_QUALITY_GATES.md").is_file():
        cons = read(DELIVERY / "CONSTITUTION.md")
        if "CODE_QUALITY_GATES" not in cons:
            warnings.append("CQG present but CONSTITUTION.md has no pointer")
    if (ROOT / "OKF_KNOWLEDGE_BUNDLE.md").is_file() or (ROOT / "knowledge").is_dir():
        cons = read(DELIVERY / "CONSTITUTION.md")
        if "OKF" not in cons and "knowledge/" not in cons:
            warnings.append("OKF/knowledge present but CONSTITUTION.md has no pointer")

    for w in warnings:
        print(f"WARNING: {w}")
    for e in errors:
        print(f"ERROR: {e}", file=sys.stderr)
    print(f"delivery_check: {len(errors)} error(s), {len(warnings)} warning(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())