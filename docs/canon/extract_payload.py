#!/usr/bin/env python3
"""Извлекатель payload'а канонов — тот самый, который канон раньше НЕ поставлял.

Едет ВМЕСТЕ с канонами (как `stack_selftest.py` и `selftest_sizes.py`), потому что
нужен ровно в момент развёртывания: достать скрипты, конфиги и шаблоны из четырёх
`*.md` и сказать, ВСЁ ли достал.

Почему канон перестал требовать свой извлекатель у каждого исполнителя. §5.0
записывала три правила разбора, «купленных ошибками», и предлагала написать по ним
свой парсер. Полевой замер обновления: чужой извлекатель нашёл **73 файла из 74** —
девятый модуль доктора обнаружился сравнением списков заголовков между ревизиями, а
не проверкой. То есть правила были известны, а дефекты разбора получались каждый раз
новые, и находились они случайно.

⚠ **Что при этом ТЕРЯЕТСЯ, и это названо, а не замолчано.** Свой парсер у каждого
развёртывания был случайным источником независимой проверки: чужой разбор спотыкался
о то, чего мой не видит. Общий инструмент эту проверку убирает — дефект разбора
становится один для всех. Смягчение: три правила остаются в §5.0 спецификацией (свой
парсер по-прежнему законен), а `--manifest` печатает список путей, чтобы своя сверка
стоила одну команду:

    python3 extract_payload.py --manifest | sort > /tmp/ожидается
    (cd <проект> && git ls-files scripts) | sort > /tmp/есть
    diff /tmp/ожидается /tmp/есть

Режимы:
    extract_payload.py                     # самопроверка: всё ли извлекается
    extract_payload.py --manifest          # пути payload'а, по одному на строку
    extract_payload.py --extract <каталог> # разложить payload в каталог
    extract_payload.py --canon-dir <путь>  # где лежат четыре *.md (дефолт: рядом)
"""

from __future__ import annotations

import argparse
import functools
import re
import sys
from pathlib import Path

#: Имена канонов по ключу. Пути НЕ зашиты: инструмент едет с канонами, но
#: сьют канон-репозитория зовёт его же со своим каталогом.
CANON_FILES = {
    "stack": "AGENT_STACK.md",
    "delivery": "AGENT_DELIVERY_HARNESS.md",
    "cqg": "CODE_QUALITY_GATES.md",
    "okf": "OKF_KNOWLEDGE_BUNDLE.md",
}

# Где лежит тело каждого файла контура. Держим здесь ПОЛНЫЙ список: развёртывание
# по заголовкам приложений давало 14 файлов из 16 — два живут в прозе (CQG §5.0
# «Инвентарь» про это же).
SCRIPTS = {
    "scripts/delivery_check.py": ("delivery", "# Приложение B — `scripts/delivery_check.py`", "python"),
    "scripts/delivery_base.py": ("delivery", "# Приложение B1 — `scripts/delivery_base.py`", "python"),
    "scripts/delivery_diff.py": ("delivery", "# Приложение B2 — `scripts/delivery_diff.py`", "python"),
    "scripts/delivery_decisions.py": ("delivery", "# Приложение B3 — `scripts/delivery_decisions.py`", "python"),
    "scripts/delivery_risk.py": ("delivery", "# Приложение B4 — `scripts/delivery_risk.py`", "python"),
    "scripts/delivery_runtime.py": ("delivery", "# Приложение B5 — `scripts/delivery_runtime.py`", "python"),
    "scripts/delivery_history.py": ("delivery", "# Приложение B6 — `scripts/delivery_history.py`", "python"),
    "scripts/delivery_status.py": ("delivery", "# Приложение B7 — `scripts/delivery_status.py`", "python"),
    "scripts/delivery_evidence.py": ("delivery", "# Приложение B8 — `scripts/delivery_evidence.py`", "python"),
    "scripts/delivery_journals.py": ("delivery", "# Приложение B9 — `scripts/delivery_journals.py`", "python"),
    "scripts/delivery_artifact.py": ("delivery", "# Приложение B11 — `scripts/delivery_artifact.py`", "python"),
    "scripts/delivery_limits.py": ("delivery", "# Приложение B10 — `scripts/delivery_limits.py`", "python"),
    "scripts/delivery_metrics.py": ("delivery", "# Приложение C — `scripts/delivery_metrics.py`", "python"),
    "scripts/lint/check_grep_gate.sh": ("cqg", "### `scripts/lint/check_grep_gate.sh`", "bash"),
    "scripts/lint/check_ast_gate.py": ("cqg", "### `scripts/lint/check_ast_gate.py`", "python"),
    "scripts/lint/check_file_length.sh": ("cqg", "### `scripts/lint/check_file_length.sh`", "bash"),
    "scripts/lint/check_complexity_gate.sh": ("cqg", "### `scripts/lint/check_complexity_gate.sh`", "bash"),
    "scripts/lint/complexity_halves.sh": ("cqg", "### `scripts/lint/complexity_halves.sh`", "bash"),
    "scripts/lint/check_new_dependency.py": ("cqg", "### `scripts/lint/check_new_dependency.py`", "python"),
    "scripts/lint/check_gate_coverage.sh": ("cqg", "### `scripts/lint/check_gate_coverage.sh`", "bash"),
    "scripts/lint/gate_coverage_roles.sh": ("cqg", "### `scripts/lint/gate_coverage_roles.sh`", "bash"),
    "scripts/lint/gate_coverage_template.sh": ("cqg", "### `scripts/lint/gate_coverage_template.sh`", "bash"),
    "scripts/lint/check_layers_gate.sh": ("cqg", "### `scripts/lint/check_layers_gate.sh`", "bash"),
    "scripts/lint/check_deps_audit.sh": ("cqg", "### `scripts/lint/check_deps_audit.sh`", "bash"),
    "scripts/lint/check_diff_coverage.sh": ("cqg", "### `scripts/lint/check_diff_coverage.sh`", "bash"),
    "scripts/lint/ast_rules.py": ("cqg", "### `scripts/lint/ast_rules.py`", "python"),
    "scripts/lint/ast_web_rules.py": ("cqg", "### `scripts/lint/ast_web_rules.py`", "python"),
    "scripts/lint/dependency_manifests.py": ("cqg", "### `scripts/lint/dependency_manifests.py`", "python"),
    # Доктор разрезан на шесть файлов (`cqg@1.82`) — планка 300 строк, §9.1a п.5.
    # Развёртывание копирует ВСЕ: без любого модуля доктор не стартует.
    "scripts/lint/contour_doctor.py": ("cqg", "### `scripts/lint/contour_doctor.py`", "python"),
    "scripts/lint/doctor_core.py": ("cqg", "### `scripts/lint/doctor_core.py`", "python"),
    "scripts/lint/doctor_layout.py": ("cqg", "### `scripts/lint/doctor_layout.py`", "python"),
    "scripts/lint/doctor_versions.py": ("cqg", "### `scripts/lint/doctor_versions.py`", "python"),
    "scripts/lint/doctor_hooks.py": ("cqg", "### `scripts/lint/doctor_hooks.py`", "python"),
    "scripts/lint/doctor_areas.py": ("cqg", "### `scripts/lint/doctor_areas.py`", "python"),
    "scripts/lint/doctor_area_verdicts.py": ("cqg", "### `scripts/lint/doctor_area_verdicts.py`", "python"),
    "scripts/lint/doctor_canaries.py": ("cqg", "### `scripts/lint/doctor_canaries.py`", "python"),
    "scripts/lint/doctor_probes.py": ("cqg", "### `scripts/lint/doctor_probes.py`", "python"),
    "scripts/lint/doctor_deployment.py": ("cqg", "### `scripts/lint/doctor_deployment.py`", "python"),
    "scripts/lint/assert_digest.sh": ("cqg", "### `scripts/lint/assert_digest.sh`", "bash"),
    "scripts/lint/check_ci_status.sh": ("cqg", "### `scripts/lint/check_ci_status.sh`", "bash"),
    "scripts/lint/check_gate_value.sh": ("cqg", "### `scripts/lint/check_gate_value.sh`", "bash"),
    "scripts/lint/check_mutation_gate.sh": ("cqg", "### `scripts/lint/check_mutation_gate.sh`", "bash"),
    "scripts/lint/mutation_ts.sh": ("cqg", "### `scripts/lint/mutation_ts.sh`", "bash"),
    "scripts/lint/mutation_py.sh": ("cqg", "### `scripts/lint/mutation_py.sh`", "bash"),
    "scripts/lint/mutation_verdict.sh": ("cqg", "### `scripts/lint/mutation_verdict.sh`", "bash"),
    "scripts/lint/check_jscpd_gate.sh": ("cqg", "### `scripts/lint/check_jscpd_gate.sh`", "bash"),
    "scripts/lint/check_eslint_warnings.sh": ("cqg", "### `scripts/lint/check_eslint_warnings.sh`", "bash"),
    "scripts/okf_validate.py": ("okf", "# Приложение B — валидатор формата (`okf_validate.py`)", "python"),
    "scripts/okf_sync_gate.py": ("okf", "# Приложение C — `scripts/okf_sync_gate.py` (гейт code ↔ canon)", "python"),
    # В прозе, не в приложении:
    "scripts/lint/check_baseline_ratchet.sh": ("cqg", "### 8.2. Новый гейт: `check_baseline_ratchet.sh`", "bash"),
    "scripts/merge_guard.sh": ("cqg", "#### 8.5.2. `scripts/merge_guard.sh`", "bash"),
}

#: Скрипт → его части. С `cqg@1.82` payload режется по планке 300 строк
#: (§9.1a п.5), и «скопировать один файл» перестало работать: без части скрипт не
#: стартует вовсе. Полигон (`harness.Lab`) разворачивает вход в комплект по этой
#: таблице — иначе каждый следующий разрез требовал бы правки всех тестов, а
#: забытый модуль давал бы падение импорта вместо проверяемого свойства.
PARTS = {
    "scripts/delivery_check.py": (
        "scripts/delivery_base.py",
        "scripts/delivery_diff.py",
        "scripts/delivery_decisions.py",
        "scripts/delivery_risk.py",
        "scripts/delivery_runtime.py",
        "scripts/delivery_history.py",
        "scripts/delivery_status.py",
        "scripts/delivery_evidence.py",
        "scripts/delivery_journals.py",
        "scripts/delivery_limits.py",
        "scripts/delivery_artifact.py",
    ),
    "scripts/lint/contour_doctor.py": (
        "scripts/lint/doctor_core.py", "scripts/lint/doctor_layout.py",
        "scripts/lint/doctor_versions.py",
        "scripts/lint/doctor_hooks.py", "scripts/lint/doctor_areas.py",
        "scripts/lint/doctor_area_verdicts.py",
        "scripts/lint/doctor_canaries.py",
        "scripts/lint/doctor_probes.py",
        "scripts/lint/doctor_deployment.py"),
    "scripts/lint/check_ast_gate.py": (
        "scripts/lint/ast_rules.py", "scripts/lint/ast_web_rules.py"),
    "scripts/lint/check_new_dependency.py": ("scripts/lint/dependency_manifests.py",),
    "scripts/lint/check_complexity_gate.sh": ("scripts/lint/complexity_halves.sh",),
    "scripts/lint/check_mutation_gate.sh": (
        "scripts/lint/mutation_ts.sh", "scripts/lint/mutation_py.sh",
        "scripts/lint/mutation_verdict.sh"),
    "scripts/lint/check_gate_coverage.sh": (
        "scripts/lint/gate_coverage_roles.sh", "scripts/lint/gate_coverage_template.sh"),
}

#: Доктор целиком: полигон обязан получить ВСЕ его файлы, иначе не стартует.
DOCTOR = ("scripts/lint/contour_doctor.py", *PARTS["scripts/lint/contour_doctor.py"])


def with_parts(rels: tuple[str, ...]) -> tuple[str, ...]:
    """Вход → вход и его части, без повторов и в устойчивом порядке."""
    out: list[str] = []
    for rel in rels:
        for item in (rel, *PARTS.get(rel, ())):
            if item not in out:
                out.append(item)
    return tuple(out)

# Конфиги и workflow'ы: путь в проекте -> (канон, маркер, язык блока).
# Отдельно от SCRIPTS, потому что счётчики прозы считают именно скрипты
# (`test_prose_matches_payload`), а инвентарь §5.0 перечисляет эти файлы строкой
# «Приложение B» / «§8.3» — то есть они payload, но не `scripts/**`.
CONFIGS = {
    ".pre-commit-config.yaml": ("cqg", "### `.pre-commit-config.yaml`", "yaml"),
    "backend/pyproject.toml": ("cqg", "### `backend/pyproject.toml (фрагмент)`", "toml"),
    "backend/.importlinter": ("cqg", "### `backend/.importlinter`", "ini"),
    ".dependency-cruiser.cjs": ("cqg", "### `.dependency-cruiser.cjs`", "javascript"),
    "backend/requirements-dev.txt": ("cqg", "### `backend/requirements-dev.txt`", "text"),
    "frontend/eslint.config.js": ("cqg", "### `<frontend>/eslint.config.js`", "javascript"),
    "frontend/.prettierrc": ("cqg", "### `<frontend>/.prettierrc`", "json"),
    ".github/workflows/quality.yml": ("cqg", "### 8.3. Workflow (GitHub Actions)", "yaml"),
    ".github/workflows/main-guard.yml": (
        "cqg", "**④ Красное на `main` не остаётся незамеченным.**", "yaml"),
    # Адаптер GitLab объявляется payload'ом наравне с workflow'ами: иначе ни один
    # тест физически не видит его, и уроки шаблона (кэш по манифесту, фронт не
    # прибит к каталогу, шаг «инструменты на месте») проверяются для ОДНОГО
    # хостинга — то есть «второй список, который никто не сверяет», от которого
    # §8.3a отговаривает, существовал бы прямо в ней самой.
    ".gitlab-ci.yml": ("cqg", "### 8.3a. GitLab: тот же контракт, тонкий адаптер", "yaml"),
}

# Шаблоны delivery/**: маркер приложения -> путь в дереве §2.3.
#: Шаблоны дерева живут ТОЛЬКО в Delivery, и это одно знание на двух
#: потребителей: `template()` читает их оттуда, `--manifest --by-canon`
#: этим же отвечает, какому канону они принадлежат. Константа вместо двух
#: литералов — `one-notion-one-place` из собственного реестра классов.
TEMPLATES_CANON = "delivery"

TEMPLATES = {
    "delivery/CONSTITUTION.md": "### A.1. ",
    "delivery/active/STATUS.md": "### A.2. ",
    "delivery/active/spec.md": "### A.3. ",
    "delivery/active/tasks.md": "### A.4. ",
    "delivery/README.md": "### A.6. ",
    "delivery/active/plan.md": "### A.7. ",
    "delivery/active/verify-report.md": "### A.8. ",
    "delivery/STACK-ACCEPTANCE.md": "### A.12. ",
    "delivery/archive/INDEX.md": "### A.13. ",
    "delivery/active/decisions.md": "### A.14. ",
    "delivery/active/diagnosis.md": "### A.15. ",
    "delivery/active/escalation.md": "### A.16. ",
    # A.9 даёт ДВА файла дерева под одним номером, поэтому второй берётся по своей
    # подписи, а не по заголовку приложения. Ровно из-за этого все три строки ниже
    # и выпадали из инвентаря: обход шёл по «### A.N», а дерево §2.3 растёт файлами.
    # Найдено регрессией на процедуру (`test_deployment_procedure`), а не чтением.
    "delivery/active/eval-smoke.md": "### A.9. ",
    "delivery/evals/smoke/README.md": "`delivery/evals/smoke/README.md`:",
    "delivery/archive/<slug>/observed.md": "### A.17. ",
}


def block_after(text: str, marker: str, lang: str) -> str:
    """Первый блок ```lang после marker, с учётом вложенности фенсов и ОТСТУПА.

    ⚠ **Фенс ищется по `lstrip()`, а тело выравнивается по отступу открывающего.**
    До `cqg@2.10` здесь стояло `line.startswith("```")`, и блоки внутри
    нумерованных списков были невидимы — а процедура развёртывания держит
    исполняемые команды именно там.

    Это было **расхождение двух ПОСТАВЛЯЕМЫХ парсеров**: `blocks()` в
    `stack_selftest.py` ту же дыру закрыл раньше («исполняемые блоки процедуры
    развёртывания не проверялись НИКОГДА»), а извлекатель остался со старым
    признаком. Развёртывание получало два разных ответа на вопрос «где здесь
    блок» — тот же класс, что второй список версий (`cqg@1.59`) и второй парсер
    payload'а (`cqg@2.08`), только молчаливый.

    Выравнивание — не косметика, и это замерено: heredoc с отступом у
    терминатора **не закрывается**, то есть блок, извлечённый «как есть»,
    исполниться не может. `bash -n` такой блок принимает (проверено), значит
    синтаксическая проверка этот класс не ловит вовсе.

    Обратный прогон обязателен и сделан: извлечение всех 75 файлов payload'а до
    и после правки совпадает побайтово — фенсы payload'а стоят в нулевой
    колонке, и для них поведение не изменилось.
    """
    if marker not in text:
        raise KeyError(f"маркер не найден: {marker!r}")
    tail = text.split(marker, 1)[1]
    out: list[str] = []
    depth = 0
    started = False
    pad = 0
    for line in tail.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("```"):
            info = stripped[3:].strip().lower()
            if not started:
                if info == lang:
                    started, depth = True, 1
                    pad = len(line) - len(stripped)
                continue
            if info:                      # вложенное открытие
                depth += 1
            else:                         # закрытие
                depth -= 1
                if depth == 0:
                    return "\n".join(out)
            out.append(line[pad:] if line[:pad].isspace() else line)
            continue
        if started:
            out.append(line[pad:] if line[:pad].isspace() else line)
    raise ValueError(f"незакрытый блок {lang} после {marker!r}")


#: Признак РАЗМЕТКИ, а не кода: заголовок markdown в начале строки или фенс.
#: Замерено на всём payload'е — ни один скрипт таких строк не содержит (0 из 48),
#: поэтому признак не даёт ложного срабатывания на коде.
_MARKDOWN = re.compile(r"(?m)^(#{2,3} \S|```)")


@functools.lru_cache(maxsize=None)
def prose_only(src: str) -> str:
    """Разметка без ТЕЛ блоков; строки сохраняются, номера не едут.

    Правильный хелпер для markdown: оракулу про документ нужно убрать примеры из
    ```-блоков, а не строки, начинающиеся с `#` (в разметке это заголовки).
    """
    out, depth = [], 0
    for line in src.splitlines():
        if line.lstrip().startswith("```"):
            info = line.lstrip()[3:].strip()
            depth += 1 if (info and depth == 0) else (-1 if not info else 0)
            depth = max(depth, 0)
            out.append("")
            continue
        out.append("" if depth else line)
    return "\n".join(out)


@functools.lru_cache(maxsize=None)
def code_only(src: str) -> str:
    """Исходник без строк-комментариев — для оракулов, которые ищут форму в КОДЕ.

    Зачем отдельный хелпер, а не три заплатки по месту. Класс сработал **трижды**:
    тест запрещал `MUT_MAJOR`, кириллический диапазон в shell-классе и упоминание
    `LINT_PY_SRC` — и каждый раз падал на комментарии, который ОБЪЯСНЯЛ запрет.
    То есть оракул наказывал документирование собственного правила, а чинилось это
    поштучно. Правило: если проверка про то, «как написан код», комментарии из неё
    исключаются здесь, а не в каждом тесте заново.

    Снимаются только строки, начинающиеся с `#` (shell, python, yaml, toml).
    Хвостовые комментарии не трогаем: `x = 1  # …` — это всё ещё строка кода, и
    форма в ней имеет значение.
    """
    # ⚠ ГРОМКО отказываемся от разметки. На markdown этот хелпер срезает все
    # заголовки (они начинаются с `#`), и оракул тихо видит пустоту: проверка
    # оглавления так насчитала НОЛЬ секций и объявила бы его полным при любом
    # содержании (`stack-map@1.44`). Тихая слепота — худший отказ проверки, а
    # значит правильное поведение здесь — упасть с адресом починки.
    if _MARKDOWN.search(src):
        raise ValueError(
            "code_only() получил разметку, а он для КОДА: на markdown он срезает "
            "все заголовки и оракул тихо видит пустоту. Для документа — prose_only()"
        )

    return "\n".join(l for l in src.splitlines() if not l.lstrip().startswith("#"))




#: Payload, который ПРИСТАВЛЯЕТСЯ к существующему файлу, а не пишется своим.
#: Ключ — как называть в отчёте, значение — (канон, уникальный маркер, язык).
#:
#: ⚠ Заведено потому, что блок хуков `pre-push` не извлекал НИ ОДИН тест
#: (`cqg@2.08`): основной `.pre-commit-config.yaml` объявлен в `CONFIGS`, а эти три
#: хука — отдельный снипет §8.6 «добавить рядом с остальными». И неверная база
#: диффа жила ровно там (`cqg@2.05`) — payload без покрытия ломается первым.
#: В манифест они НЕ входят: манифест сверяется с `git ls-files` проекта, а своего
#: файла у снипета нет. Зато входят в самопроверку — извлекаются и парсятся.
SNIPPETS = {
    "pre-push hooks (§8.6)": (
        "cqg", "# .pre-commit-config.yaml — добавить рядом с остальными", "yaml"),
}


class Payload:
    """Payload одного каталога канонов: чтение, извлечение, манифест."""

    def __init__(self, canon_dir: str | Path) -> None:
        self.dir = Path(canon_dir).resolve()

    def path(self, key: str) -> Path:
        return self.dir / CANON_FILES[key]

    def canon_text(self, key: str) -> str:
        """Текст канона; кэш САМ замечает правку файла.

        ⚠ Раньше кэш стоял на одном лишь имени и переживал любую правку на диске.
        Для сьюта это верно (каноны при прогоне не меняются), а для инструмента,
        который канон ПРАВИТ, — ловушка: за одну сессию она сработала дважды.
        Проверка «парсится ли скрипт после выреза» читала ПРЕДЫДУЩУЮ версию и
        печатала ✓ на сломанном файле — то есть собственная страховка врала
        зелёным, а это худший отказ проверки из возможных.

        Ключ включает `mtime` и размер: правка файла делает ключ новым.
        """
        p = self.path(key)
        st = p.stat()
        return _cached_text(str(p), st.st_mtime, st.st_size)

    def script(self, rel: str) -> str:
        key, marker, lang = SCRIPTS[rel]
        return block_after(self.canon_text(key), marker, lang)

    def template(self, rel: str) -> str:
        return block_after(self.canon_text(TEMPLATES_CANON), TEMPLATES[rel], "markdown")

    def config(self, rel: str) -> str:
        key, marker, lang = CONFIGS[rel]
        return block_after(self.canon_text(key), marker, lang)

    def whole(self, rel: str) -> str:
        return "\n".join(self.script(r) for r in with_parts((rel,)))

    def body(self, rel: str) -> str:
        """Тело по пути — из любого инвентаря. Манифест един, а разделы разные."""
        if rel in SCRIPTS:
            return self.script(rel)
        if rel in CONFIGS:
            return self.config(rel)
        return self.template(rel)

    def snippet(self, name: str) -> str:
        """Тело приставляемого фрагмента (`SNIPPETS`).

        Маркер здесь — строка ВНУТРИ блока, а не заголовок перед ним: у снипета
        нет своего `###`, и попытка взять «первый ```yaml после install --hook-type
        pre-push» приводит к чужому блоку (workflow), потому что та же строка есть
        и в §5. Признак взят уникальный — это проверено счётом вхождений.
        """
        key, marker, _lang = SNIPPETS[name]
        text = self.canon_text(key)
        start = text.index(marker)
        return text[start:text.index("```", start)]

    @staticmethod
    def manifest() -> list[str]:
        """ВСЕ пути payload'а: скрипты, конфиги, шаблоны. Один список, не три.

        Это ответ на «нашлось 73 из 74»: полноту сверяют diff'ом, а не глазами
        по таблице §5.0.
        """
        return sorted({*SCRIPTS, *CONFIGS, *TEMPLATES})

    def extract_all(self, dest: str | Path) -> list[str]:
        """Разложить payload в каталог. Возвращает пути, которые записал."""
        root = Path(dest)
        written = []
        for rel in self.manifest():
            p = root / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(self.body(rel) + "\n", encoding="utf-8")
            if rel.endswith(".sh"):
                p.chmod(0o755)
            written.append(rel)
        return written


@functools.lru_cache(maxsize=None)
def _cached_text(path: str, mtime: float, size: int) -> str:
    """Кэш ПО ОТПЕЧАТКУ файла: ключ включает mtime и размер."""
    return Path(path).read_text(encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--canon-dir", default=str(Path(__file__).resolve().parent))
    ap.add_argument("--manifest", action="store_true")
    # ⚠ Отдельный флаг, а не смена формата `--manifest`: его вывод («путь на
    # строку») стоит в рецепте сверки в шапке этого файла и в §5.0, и менять
    # его значило бы сломать чужие однострочники ради своего потребителя.
    #
    # Зачем канон вообще нужен в выводе: снимок в проекте несёт ВСЕ четыре
    # канона даже там, где развёрнуто три (вариант A/B). Кто судит полноту
    # состава, обязан выбросить payload канона, объявленного `@absent`, иначе
    # он обвинит законную раскладку — а ложное срабатывание снимают вместе с
    # проверкой (§4.3b).
    ap.add_argument("--by-canon", action="store_true",
                    help="с --manifest: печатать `канон<TAB>путь`")
    ap.add_argument("--extract", metavar="DIR")
    args = ap.parse_args(argv)
    pl = Payload(args.canon_dir)

    if args.manifest:
        if args.by_canon:
            owner = {rel: spec[0] for rel, spec in {**SCRIPTS, **CONFIGS}.items()}
            print("\n".join(f"{owner.get(rel, TEMPLATES_CANON)}\t{rel}"
                             for rel in pl.manifest()))
        else:
            print("\n".join(pl.manifest()))
        return 0

    if args.extract:
        written = pl.extract_all(args.extract)
        print(f"разложено файлов: {len(written)} в {args.extract}")
        return 0

    bad = 0
    for rel in pl.manifest():
        try:
            print(f"  {rel}: {len(pl.body(rel).splitlines())} строк")
        except Exception as exc:  # noqa: BLE001
            print(f"  {rel}: ОШИБКА {exc}")
            bad += 1
    for name in SNIPPETS:
        try:
            print(f"  [фрагмент] {name}: {len(pl.snippet(name).splitlines())} строк")
        except Exception as exc:  # noqa: BLE001
            print(f"  [фрагмент] {name}: ОШИБКА {exc}")
            bad += 1
    total = len(pl.manifest()) + len(SNIPPETS)
    print(f"\npayload: {total - bad} из {total} извлечено"
          + (f", ОШИБОК {bad}" if bad else ""))
    print(f"  файлов {len(pl.manifest())} (скриптов {len(SCRIPTS)}, "
          f"конфигов {len(CONFIGS)}, шаблонов {len(TEMPLATES)}) "
          f"+ фрагментов {len(SNIPPETS)}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
