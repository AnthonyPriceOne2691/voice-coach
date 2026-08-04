#!/usr/bin/env python3
"""Диагностика РАЗВЁРНУТОГО контура: что здесь работает, что бедно, что мертво.

Зачем отдельный инструмент, когда есть мета-гейт. `check_gate_coverage.sh`
отвечает «вписан ли гейт в конфиг» — это текст. Между «вписан» и «судит» лежит
целый класс отказов, и он не гипотетический: за одну сессию 2026-08-03 нашлось
пять случаев, все замерены. Мутационный гейт не судил на дефолтной раскладке
(ключи мутантов не совпадали с путями импорта). Сканер незаполненных шаблонов был
мёртв под `LC_ALL=C` — GNU grep ругался на кириллический диапазон и не находил
ничего. `new-dependency` был CI-only на проекте без раннера, то есть не исполнялся
ни разу за поставку. `deps-audit` на отсутствующем инструменте выходит нулём, и
сводка pre-commit печатает `Passed`. Сам CI был красным восемь пушей подряд, пока
локально было зелено.

Ни один из этих отказов не виден ни мета-гейту (он смотрит конфиг), ни сьюту
(он про канон, а не про этот проект), ни `check_gate_value.sh` (ему нужна история
срабатываний из живого CI).

**Принцип: пробовать ИСПОЛНЕНИЕМ, а не чтением.** Каждому гейту подсовывается его
собственная канарейка — файл с заведомым нарушением ровно того класса, который
гейт стережёт, — и проверяется, что гейт краснеет. Гейт, промолчавший на своей
канарейке, объявляется **DEAD**: это не бедность, это ложь, и только она роняет
доктора. Отсутствие инструмента (`ABSENT`) и мягкий пропуск с названной причиной
(`WEAK`) — честная непокрытость, exit 0.

Это ИНСТРУМЕНТ, не гейт: слот бюджета §9.1a он не занимает (как
`check_gate_value.sh` и `assert_digest.sh`) и в pre-commit не вписывается.

Запуск из корня проекта с развёрнутым контуром:

    python3 scripts/lint/contour_doctor.py            # таблица + вердикт
    python3 scripts/lint/contour_doctor.py --json     # машинно-читаемо
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# --- вердикты ----------------------------------------------------------------
AUTO = "AUTO"      # проверено исполнением: канарейка покраснела
WEAK = "WEAK"      # работает, но не судит; причина названа самим гейтом
DEAD = "DEAD"      # объявлен и вписан — и молчит на своей канарейке. Только это ложь
ABSENT = "ABSENT"  # не развёрнут
SKIP = "SKIP"      # доктор не умеет это пробовать — назвать, а не умолчать
TOOL = "TOOL"      # это не гейт, а измерительный инструмент: судить его нечем

ORDER = {DEAD: 0, SKIP: 1, WEAK: 2, ABSENT: 3, TOOL: 4, AUTO: 5}
COLOR = {AUTO: "\033[32m", WEAK: "\033[33m", DEAD: "\033[31m",
         ABSENT: "\033[90m", SKIP: "\033[36m", TOOL: "\033[90m"}
RESET = "\033[0m"

CANONS = ("AGENT_STACK.md", "AGENT_DELIVERY_HARNESS.md",
          "CODE_QUALITY_GATES.md", "OKF_KNOWLEDGE_BUNDLE.md")

# Инструменты, на которых стоят гейты. `timeout` отдельно: он GNU coreutils и на
# macOS отсутствует по умолчанию — без него мутационный гейт пропускается.
TOOLS = {
    "ruff": "гейт сложности, основной линт",
    "mypy": "типы",
    "detect-secrets": "secrets-гейт (§2.7)",
    "pip-audit": "deps-audit, python-половина",
    "mutmut": "mutation — «тесты утверждают» (§3.7)",
    "jscpd": "DRY-гейт",
    "npm": "deps-audit, js-половина; eslint-ратчет",
    "timeout": "бюджет мутационного гейта (macOS: brew install coreutils)",
}

# Канарейка = «файл с нарушением ровно этого класса». Ключ — имя правила из
# `--list-rules`, чтобы список правил брался у СКРИПТА, а не дублировался здесь:
# правило, для которого канарейки нет, попадает в SKIP по имени, а не пропадает.
CANARIES: dict[str, tuple[str, str]] = {
    # grep-правила
    "config-access": ("canary.py", "import os\nX = os.getenv('SECRET')\n"),
    "di-indirection": ("canary.py", "from importlib import import_module\n"
                                    "m = import_module('pkg.sub')\n"),
    "service-no-web": ("service.py", "from fastapi import APIRouter\nr = APIRouter()\n"),
    "no-grab-bag-module": ("utils.py", "def helper():\n    return 1\n"),
    "blind-error": ("canary.py", 'def f():\n    raise Exception("bad")\n'),
    "unstructured-log": ("canary.py", "import logging\n"
                                      "logger = logging.getLogger(__name__)\n"
                                      "def f(url):\n"
                                      '    logger.info(f"fetch {url}")\n'),
    # ast-правила
    "silent-except": ("canary.py", "def f():\n    try:\n        pass\n"
                                   "    except Exception:\n        pass\n"),
    "inline-prompt": ("canary.py", 'P = """ты — помощник\n' + "строка\n" * 8 + '"""\n'),
    "cpu-in-async": ("canary.py", "import json\n"
                                  "async def f(rows):\n"
                                  "    for r in rows:\n"
                                  "        json.loads(r)\n"),
    # Односложные гейты: ключ — имя скрипта, у них нет `--list-rules`.
    "check_file_length.sh": ("huge.py", "x = 1\n" * 700),
    "check_complexity_gate.sh": ("complex.py",
        "def f(a):\n" + "".join(f"    if a == {i}:\n        return {i}\n"
                                for i in range(14))),
    "unbounded-list": ("canary.py", "from fastapi import APIRouter\n"
                                    "router = APIRouter()\n\n\n"
                                    '@router.get("/all")\n'
                                    "async def all_items() -> list[dict]:\n"
                                    "    return await repo.everything()\n"),
}


# Не гейты: измерительные инструменты и сам доктор. Канарейку им подсовывать
# бессмысленно — они ничего не запрещают. Раньше они попадали в SKIP и раздували
# «непробовано», то есть доктор преувеличивал свою слепоту.
NOT_GATES = {"check_gate_value.sh", "assert_digest.sh", "contour_doctor.py"}

# Гейты, стоящие на внешнем инструменте. Прямая канарейка требует самого
# инструмента (сеть, npm, venv), поэтому пробуется ДРУГОЕ свойство, и оно важнее:
# **честность пропуска**. Отсутствие инструмента гейт обязан НАЗВАТЬ и не выдать за
# успех. Это не теория: класс ловился трижды — `timeout` на macOS (F14), голый
# `command -v` у secrets-хука (F10), `deps_audit_waiver: no` как разрешение.
TOOL_DEPENDENT = {
    "check_jscpd_gate.sh": "jscpd",
    "check_deps_audit.sh": "pip-audit / npm",
    "check_mutation_gate.sh": "mutmut",
    "check_eslint_warnings.sh": "eslint / npm",
    "check_diff_coverage.sh": "pytest-cov",
    "check_ci_status.sh": "gh",
    "check_complexity_gate.sh": "ruff",
}

# `PATH` без homebrew и venv: coreutils и git на месте, а jscpd/mutmut/gh/ruff —
# нет. Та же раскладка, что в сьюте канона (`tests/`), и она не выдумана: гейты
# ищут инструмент через `command -v`, а живут эти инструменты вне /usr/bin.
BARE_PATH = "/usr/bin:/bin"

# Слова, которыми гейт называет пропуск. Если пропуск назван — это WEAK (бедность),
# если гейт при этом заявляет успех — DEAD (ложь).
SKIP_WORDS = ("пропущен", "не судит", "не проверен", "нет каталога", "ПРОПУЩЕНА",
              "WARNING", "не найден", "недоступен", "не смог")
SUCCESS_WORDS = (": OK", "OK —", "OK -")


def run(cmd: list[str], cwd: Path, env: dict | None = None) -> tuple[int, str]:
    e = {**os.environ, **(env or {})}
    try:
        p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True,
                           timeout=180, env=e)
    except (subprocess.TimeoutExpired, OSError) as exc:
        return 124, f"{exc}"
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def _setup_gate_coverage(lab: Path) -> tuple[list[str], dict]:
    """Скрипт лежит в `scripts/lint`, но в конфиге его нет → мета-гейт краснеет.

    Именно этот случай и породил мета-гейт: jscpd был извлечён, адаптирован и не
    вписан, а приёмка показала 7/7 зелёных.
    """
    (lab / ".pre-commit-config.yaml").write_text(
        "repos:\n  - repo: local\n    hooks:\n      - id: nothing\n"
        "        name: ничего не подключает\n        entry: true\n"
        "        language: system\n", encoding="utf-8")
    (lab / "scripts" / "lint" / "check_orphan_gate.sh").write_text(
        "#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
    return [], {}


def _setup_new_dependency(lab: Path) -> tuple[list[str], dict]:
    """Пакет добавлен в манифест и НЕ объявлен в STATUS → гейт краснеет."""
    (lab / "backend").mkdir(exist_ok=True)
    man = lab / "backend" / "pyproject.toml"
    man.write_text('[project]\nname = "app"\ndependencies = ["pydantic>=2.0"]\n',
                   encoding="utf-8")
    (lab / "delivery" / "active").mkdir(parents=True, exist_ok=True)
    (lab / "delivery" / "active" / "STATUS.md").write_text(
        "# STATUS\n\n- class: S\n", encoding="utf-8")
    run(["git", "add", "-A"], lab)
    run(["git", "-c", "user.email=d@d", "-c", "user.name=d",
         "commit", "-qm", "manifest"], lab)
    run(["git", "branch", "-f", "b0"], lab)
    man.write_text('[project]\nname = "app"\n'
                   'dependencies = ["pydantic>=2.0", "httpx>=0.27"]\n', encoding="utf-8")
    run(["git", "add", "-A"], lab)
    run(["git", "-c", "user.email=d@d", "-c", "user.name=d",
         "commit", "-qm", "add dep"], lab)
    return [], {"BASE": "b0"}


def _setup_baseline_ratchet(lab: Path) -> tuple[list[str], dict]:
    """Снимок переснят ВВЕРХ → легализация свежих нарушений, гейт краснеет."""
    base = lab / "scripts" / "lint" / "file_length_baseline.txt"
    base.write_text("# снимок\n[baseline]\n120:backend/features/a.py\n", encoding="utf-8")
    run(["git", "add", "-A"], lab)
    run(["git", "-c", "user.email=d@d", "-c", "user.name=d",
         "commit", "-qm", "baseline"], lab)
    run(["git", "branch", "-f", "b0"], lab)
    base.write_text("# снимок\n[baseline]\n400:backend/features/a.py\n", encoding="utf-8")
    run(["git", "add", "-A"], lab)
    run(["git", "-c", "user.email=d@d", "-c", "user.name=d",
         "commit", "-qm", "raise snapshot"], lab)
    return [], {"BASE": "b0"}


# Гейты со своей постановкой: канарейка тут — не файл с нарушением, а СОСТОЯНИЕ
# репозитория (несвязанный скрипт, необъявленная зависимость, поднятый снимок).
DIRECT_SETUP = {
    "check_gate_coverage.sh": _setup_gate_coverage,
    "check_new_dependency.py": _setup_new_dependency,
    "check_baseline_ratchet.sh": _setup_baseline_ratchet,
}


class Doctor:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.rows: list[tuple[str, str, str]] = []

    def add(self, verdict: str, point: str, detail: str) -> None:
        self.rows.append((verdict, point, detail))

    # --- A. каноны -----------------------------------------------------------
    def check_canons(self) -> None:
        for name in CANONS:
            p = self.root / name
            if not p.is_file():
                self.add(ABSENT, f"канон {name}", "файла нет — слой не развёрнут")
                continue
            m = re.search(r"\*\*Canon version:\*\*\s*`([^`]+)`", p.read_text("utf-8")) \
                or re.search(r"\*\*Эта карта:\*\*\s*`([^`]+)`", p.read_text("utf-8"))
            self.add(AUTO if m else WEAK, f"канон {name}",
                     f"версия {m.group(1)}" if m else "версия в шапке не читается")

    # --- B. места принуждения ------------------------------------------------
    def check_enforcement(self) -> None:
        cfg = self.root / ".pre-commit-config.yaml"
        self.add(AUTO if cfg.is_file() else ABSENT, "конфиг pre-commit",
                 "есть" if cfg.is_file() else "нет — коммит-гейтов не существует")

        # Установлен ли хук ФАКТИЧЕСКИ. Конфиг без `pre-commit install` — это
        # список пожеланий: ни один хук не запустится, и об этом ничто не скажет.
        for hook in ("pre-commit", "pre-push"):
            h = self.root / ".git" / "hooks" / hook
            if h.is_file() and "pre-commit" in h.read_text("utf-8", errors="ignore"):
                self.add(AUTO, f"хук {hook} установлен", str(h.relative_to(self.root)))
            else:
                self.add(DEAD if cfg.is_file() else ABSENT, f"хук {hook} установлен",
                         "конфиг есть, а хук НЕ установлен: `pre-commit install"
                         f"{' --hook-type pre-push' if hook == 'pre-push' else ''}`"
                         if cfg.is_file() else "нет")

        wf = sorted((self.root / ".github" / "workflows").glob("*.y*ml")) \
            if (self.root / ".github" / "workflows").is_dir() else []
        self.add(AUTO if wf else ABSENT, "CI workflow",
                 ", ".join(p.name for p in wf) if wf else "нет — §10.4 закроет как weak")

        mg = self.root / "scripts" / "merge_guard.sh"
        self.add(AUTO if mg.is_file() else ABSENT, "гейт мержа merge_guard.sh",
                 "есть" if mg.is_file() else "нет — мерж не проверяет слитое состояние")

    # --- C. инструменты ------------------------------------------------------
    def check_tools(self) -> None:
        venvs = [self.root / ".venv" / "bin", self.root / "backend" / ".venv" / "bin"]
        for tool, why in TOOLS.items():
            found = next((str(v / tool) for v in venvs if (v / tool).is_file()), None) \
                or shutil.which(tool) \
                or (shutil.which("gtimeout") if tool == "timeout" else None)
            self.add(AUTO if found else ABSENT, f"инструмент {tool}",
                     found if found else f"нет → {why} не работает")

    # --- D. снимки -----------------------------------------------------------
    def check_snapshots(self) -> None:
        d = self.root / "scripts" / "lint"
        if not d.is_dir():
            self.add(ABSENT, "снимки гейтов", "нет scripts/lint — контур не развёрнут")
            return
        found = sorted(p.name for p in d.glob("*baseline*.txt"))
        self.add(AUTO if found else WEAK, "снимки (baseline)",
                 f"{len(found)} шт: {', '.join(found)}" if found
                 else "ни одного: гейт без снимка красный на первом коммите, "
                      "и его снимают")

    # --- E. канарейки: главное ----------------------------------------------
    def _rules_of(self, script: Path) -> list[str]:
        """Список правил берётся У СКРИПТА (`--list-rules`), не дублируется тут."""
        cmd = ["python3", str(script)] if script.suffix == ".py" else ["bash", str(script)]
        code, out = run(cmd + ["--list-rules"], self.root)
        if code != 0:
            return []
        return [l.strip() for l in out.splitlines() if l.strip() and " " not in l.strip()]

    def check_canaries(self) -> None:
        d = self.root / "scripts" / "lint"
        if not d.is_dir():
            self.add(ABSENT, "проба канарейкой", "нет scripts/lint")
            return
        for script in sorted(d.glob("*")):
            if not script.is_file():
                continue
            name = script.name
            if name in NOT_GATES or name == "contour_doctor.py":
                self.add(TOOL, f"{name}", "измерительный инструмент, не гейт — "
                                          "канарейке нечего ловить")
                continue
            if not name.startswith("check_"):
                continue
            if name in TOOL_DEPENDENT:
                self._probe_honest_skip(script, TOOL_DEPENDENT[name])
                continue
            if name in DIRECT_SETUP:
                self._probe_state(script, DIRECT_SETUP[name])
                continue
            rules = self._rules_of(script)
            if rules:
                for rule in rules:
                    self._probe(script, rule)
            else:
                # Односложный гейт: `--rule` он не принимает, канарейка ищется по
                # имени скрипта. Прежняя версия отправляла такие в SKIP целиком —
                # то есть доктор не пробовал file-length и сложность вообще.
                self._probe(script, None)

    def _probe_state(self, script: Path, setup) -> None:
        """Канарейка — СОСТОЯНИЕ репозитория, а не файл с нарушением в коде."""
        point = f"канарейка {script.name}"
        with tempfile.TemporaryDirectory(prefix="doctor-state-") as tmp:
            lab = Path(tmp)
            (lab / "scripts" / "lint").mkdir(parents=True)
            (lab / "backend" / "features").mkdir(parents=True)
            (lab / "backend" / "features" / "a.py").write_text("x = 1\n", encoding="utf-8")
            shutil.copy(script, lab / "scripts" / "lint" / script.name)
            run(["git", "init", "-q", "."], lab)
            run(["git", "add", "-A"], lab)
            run(["git", "-c", "user.email=d@d", "-c", "user.name=d",
                 "commit", "-qm", "base"], lab)
            extra_args, extra_env = setup(lab)
            cmd = (["python3"] if script.suffix == ".py" else ["bash"]) \
                + [str(lab / "scripts" / "lint" / script.name)] + extra_args
            code, out = run(cmd, lab, env={"LINT_PY_SRC": "backend/features",
                                           **extra_env})
            if code != 0:
                self.add(AUTO, point, "канарейка поймана")
            elif any(w in out for w in SKIP_WORDS):
                self.add(WEAK, point, out.strip().splitlines()[0][:78])
            else:
                self.add(DEAD, point,
                         f"МОЛЧИТ на подготовленном нарушении: {out.strip()[:66]!r}")

    def _probe_honest_skip(self, script: Path, tool: str) -> None:
        """Инструмента нет — гейт обязан НАЗВАТЬ пропуск и не выдать его за успех.

        Прямая канарейка тут потребовала бы самого инструмента (сеть, npm, venv), а
        это свойство важнее и проверяется без него. Класс ловился трижды: `timeout`
        на macOS ронял мутационный гейт в «мутанты не сгенерированы» и exit 0 (F14);
        secrets-хук с голым `command -v` печатал `Passed`, не просмотрев ни файла
        (F10); `deps_audit_waiver: no` работал как разрешение при critical=1.
        """
        point = f"честный пропуск {script.name} (нет {tool})"
        with tempfile.TemporaryDirectory(prefix="doctor-skip-") as tmp:
            lab = Path(tmp)
            (lab / "backend" / "features").mkdir(parents=True)
            (lab / "scripts" / "lint").mkdir(parents=True)
            shutil.copy(script, lab / "scripts" / "lint" / script.name)
            run(["git", "init", "-q", "."], lab)
            run(["git", "add", "-A"], lab)
            run(["git", "-c", "user.email=d@d", "-c", "user.name=d",
                 "commit", "-qm", "base"], lab)
            run(["git", "branch", "-f", "b0"], lab)
            # Изменённый prod-файл появляется ПОСЛЕ базы: иначе диффа нет, гейт
            # честно скажет «изменённых prod-файлов нет», а доктор примет честный
            # ответ за ложь. Первая версия пробы делала ровно так и дала ложный
            # DEAD у diff-coverage — неверна была проба, а не гейт.
            (lab / "backend" / "features" / "a.py").write_text(
                "def f(x):\n    return x + 1\n", encoding="utf-8")
            run(["git", "add", "-A"], lab)
            run(["git", "-c", "user.email=d@d", "-c", "user.name=d",
                 "commit", "-qm", "change"], lab)
            cmd = (["python3"] if script.suffix == ".py" else ["bash"]) \
                + [str(lab / "scripts" / "lint" / script.name)]
            code, out = run(cmd, lab, env={"PATH": BARE_PATH, "BASE": "b0",
                                           "LINT_PY_SRC": "backend/features",
                                           "MUTATION_NO_BUDGET": "0"})
            named = any(w in out for w in SKIP_WORDS)
            claims_ok = any(w in out for w in SUCCESS_WORDS)
            # Заявленный успех бьёт названный пропуск, а не наоборот. Гейт может
            # шепнуть «○ пропущено: …» в теле и напечатать `: OK` в итоге — читают
            # итог, и сводка pre-commit показывает `Passed`. Это форма F10, и она
            # DEAD, даже если пропуск где-то упомянут.
            # Проверено обратным прогоном: пока это условие стояло как
            # `claims_ok and not named`, переменная была МЁРТВОЙ — вердикт давала
            # финальная ветка, и опустошение SUCCESS_WORDS ничего не меняло.
            if claims_ok:
                self.add(DEAD, point,
                         f"инструмента НЕТ, а гейт заявляет успех: {out.strip()[:70]!r}")
            elif named:
                self.add(WEAK, point, out.strip().splitlines()[0][:78])
            elif code != 0:
                self.add(AUTO, point, "инструмента нет → гейт краснеет, а не молчит")
            else:
                self.add(DEAD, point,
                         f"пропуск НЕ НАЗВАН и не красный: {out.strip()[:70]!r}")

    def _probe(self, script: Path, rule: str | None) -> None:
        point = f"канарейка {script.name}" + (f":{rule}" if rule else "")
        canary = CANARIES.get(rule or script.name)
        if canary is None:
            self.add(SKIP, point, "канарейки для этого правила у доктора нет — "
                                  "правило НЕ проверено исполнением")
            return
        fname, body = canary
        with tempfile.TemporaryDirectory(prefix="doctor-") as tmp:
            lab = Path(tmp)
            src = lab / "backend" / "features"
            src.mkdir(parents=True)
            (src / fname).write_text(body, encoding="utf-8")
            (lab / "scripts" / "lint").mkdir(parents=True)
            shutil.copy(script, lab / "scripts" / "lint" / script.name)
            run(["git", "init", "-q", "."], lab)
            run(["git", "add", "-A"], lab)
            run(["git", "-c", "user.email=d@d", "-c", "user.name=d",
                 "commit", "-qm", "canary"], lab)
            cmd = (["python3"] if script.suffix == ".py" else ["bash"]) \
                + [str(lab / "scripts" / "lint" / script.name)]
            if rule:
                cmd += ["--rule", rule]
            code, out = run(cmd, lab, env={"LINT_PY_SRC": "backend/features"})
            named_skip = any(w in out for w in
                             ("пропущен", "не судит", "не проверен", "нет каталога"))
            if code != 0:
                self.add(AUTO, point, "канарейка поймана")
            elif named_skip:
                self.add(WEAK, point, out.strip().splitlines()[0][:80])
            else:
                self.add(DEAD, point,
                         f"МОЛЧИТ на своём же нарушении (exit 0): {out.strip()[:70]!r}")

    # --- вывод ---------------------------------------------------------------
    def report(self, as_json: bool) -> int:
        dead = [r for r in self.rows if r[0] == DEAD]
        if as_json:
            print(json.dumps({
                "verdicts": [{"verdict": v, "point": p, "detail": d}
                             for v, p, d in self.rows],
                "counts": {k: sum(1 for r in self.rows if r[0] == k) for k in ORDER},
                "dead": len(dead),
            }, ensure_ascii=False, indent=2))
            return 1 if dead else 0

        for verdict, point, detail in sorted(self.rows, key=lambda r: (ORDER[r[0]], r[1])):
            print(f"{COLOR[verdict]}{verdict:6}{RESET} {point:44} {detail}")

        counts = {k: sum(1 for r in self.rows if r[0] == k) for k in ORDER}
        print(f"\ncontour-doctor: AUTO {counts[AUTO]} · WEAK {counts[WEAK]} · "
              f"ABSENT {counts[ABSENT]} · TOOL {counts[TOOL]} · "
              f"SKIP {counts[SKIP]} · DEAD {counts[DEAD]}")
        # Примечание про SKIP печатается ТОЛЬКО когда они есть. Иначе доктор
        # объявлял бы слепоту, которой у него нет, — а преувеличенная скромность
        # так же уводит от правды, как преувеличенная уверенность.
        if counts[SKIP]:
            print("SKIP — область, которую доктор не пробовал: это его собственная "
                  "непокрытость,\nи она названа, а не спрятана.")
        if dead:
            print(f"\n\033[31mERROR{RESET}: {len(dead)} проверк(и) объявлены и МОЛЧАТ "
                  "на своём же нарушении.")
            print("Это не бедность (ABSENT/WEAK честны и не роняют доктора), а ложь: "
                  "контур\nсообщает о защите, которой нет.")
            return 1
        print("\nЛжи нет: всё объявленное либо судит, либо честно названо непокрытым.")
        return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="диагностика развёрнутого контура")
    ap.add_argument("--json", action="store_true", help="машинно-читаемый вывод")
    ap.add_argument("--root", default=None, help="корень проекта (по умолчанию — git-root)")
    args = ap.parse_args()

    root = Path(args.root) if args.root else None
    if root is None:
        code, out = run(["git", "rev-parse", "--show-toplevel"], Path.cwd())
        root = Path(out.strip()) if code == 0 and out.strip() else Path.cwd()

    doc = Doctor(root.resolve())
    doc.check_canons()
    doc.check_enforcement()
    doc.check_tools()
    doc.check_snapshots()
    doc.check_canaries()
    return doc.report(args.json)


if __name__ == "__main__":
    sys.exit(main())