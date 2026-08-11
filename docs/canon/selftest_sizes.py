#!/usr/bin/env python3
"""Объявленная стоимость чтения сверяется с ИЗМЕРЕННОЙ (`stack-map@1.43`).

**Собственный класс контура, сработавший на самом контуре.** Канон объявляет, во
что обходится чтение — «канон ≈710 строк, payload ≈1320, 65% файла» в CQG §0 и
таблица размеров в карте. На этих числах стоит вся навигация: агент решает по ним,
что читать, а что не открывать. Замер 2026-08-07 (внешняя рецензия + перепроверка):

    объявлено ≈2030 строк · факт 9275 (×4.6)
    баннер payload говорит о себе «строки ~710–2029» · стоит на 2597 (×3.3)
    таблица карты: CQG 3700 · факт 9275 (×2.5); Delivery 3010 · факт 5506 (×1.8)
    OKF 1410 · факт 1467 — единственное точное объявление

Два вывода, и оба неприятные: про CQG канон утверждал ДВЕ разные цифры, и обе
неверны; а рядом с таблицей стоял html-комментарий «при правке канона пересчитывай
здесь же» — то есть правило было записано прозой и ручное. Это ровно то, что канон
говорит про любое правило без гейта: живёт, пока его читают.

Границу «канон / payload» берём у баннера `⬇ BOOTSTRAP PAYLOAD` — он и так
единственный признак раздела, никакого второго источника правды не заводим.

Допуск ±10%: объявление живёт в прозе и округляется, «≈710» против 730 — не ложь.
Расхождение в разы — ложь, и её ловим.
"""

from __future__ import annotations

import re

#: Насколько объявление может отстать от факта, оставаясь честным округлением.
TOLERANCE = 0.10

BANNER = re.compile(r"^>?\s*#*\s*⬇[^\n]*BOOTSTRAP PAYLOAD([^\n]*)", re.M)

#: `(строки ~710–2029, 65% файла)` — баннер описывает САМ СЕБЯ, и это объявление
#: тоже гниёт: до `stack-map@1.43` он говорил «~710», стоя на строке 2597.
BANNER_CLAIM = re.compile(r"строк[аи]?\s*~?(\d+)\s*[–—-]\s*~?(\d+)")
PERCENT = re.compile(r"(\d+)\s*%")

#: Проза §0: «Канон — §1–§8 (≈710 строк)» + «payload (≈1320 строк, 65% файла)».
#:
#: ⚠ Первая редакция требовала у payload'а ФОРМУ CQG — «строк» и процент внутри
#: скобок. Замер: из трёх канонов её держит один. Delivery пишет «payload
#: (≈3350)», OKF — «payload (≈670 строк)», и **оба объявления оракул не находил
#: вовсе**, а оба к тому же врали (3350 против 3750, 670 против 774 — сверх
#: допуска). Проверка молчала не потому, что расхождения нет, а потому что искала
#: одну запись из трёх: класс «правка на форму вместо правки на свойство».
#: Свойство — «в скобках после слова payload стоит число», всё остальное вольно.
PROSE_CANON = re.compile(r"Канон[^\n]*?\(≈?~?(\d+)\s*строк")
PROSE_PAYLOAD = re.compile(r"payload\*{0,2}\s*\(≈?~?(\d+)")

#: Абзац объявления существует. Если он есть и payload есть, а числа нет —
#: сверять нечего, и это тише протухшего объявления: следующая форма записи
#: снова уедет из-под проверки.
PROSE_MARK = re.compile(r"\*\*Стоимость чтения")


def cost_paragraph(text: str) -> str:
    """Абзац «Стоимость чтения» — и только он. Нет абзаца → пустая строка.

    ⚠ Без этой границы вольная регулярка читает ЛЮБУЮ прозу про payload как
    объявление файла о себе: в карте есть фраза «его собственный payload (49
    скрипт и …)», и оракул объявил её протухшим объявлением ×49 — при том что
    карта размеры объявляет таблицей, а не абзацем. Ложное срабатывание тут
    дороже пропуска (§4.3b): по нему снимают проверку целиком.
    """
    m = PROSE_MARK.search(text)
    if not m:
        return ""
    tail = text[m.start():]
    end = re.search(r"\n[ \t]*\n", tail)
    return tail[:end.start()] if end else tail

#: Строка таблицы карты: `| CQG | §0–§8, ~1410 строк | Приложения A–B, ~2290 |`.
TABLE_ROW = re.compile(r"^\|\s*(Delivery|CQG|OKF)\s*\|[^|]*?~?(\d+)\s*строк[^|]*\|"
                       r"[^|]*?~?(\d+)\s*\|", re.M)

#: Ярлык слоёв в той же строке: `§0–§12` обязан покрывать последнюю секцию файла.
TABLE_LABEL = re.compile(r"^\|\s*(Delivery|CQG|OKF)\s*\|\s*§\d+[–—-]§(\d+)", re.M)

LAYER_FILE = {"Delivery": "AGENT_DELIVERY_HARNESS.md",
              "CQG": "CODE_QUALITY_GATES.md",
              "OKF": "OKF_KNOWLEDGE_BUNDLE.md"}


def outside_fences(text: str) -> str:
    """Текст без содержимого блоков; строки сохраняются, чтобы номера не поехали.

    ⚠ Иначе оракул читает ПРИМЕР из блока и наказывает за документирование
    собственного правила: этот файл поставляется payload'ом карты, а в его
    докстринге стоят числа находки («≈710 строк, ≈1320, 65%») — и проверка
    объявила их объявлением самой карты. Класс, ради которого в сьюте живёт
    `extract.code_only()`, и третий его рецидив за день (`cqg@1.74`, `1.80`).
    """
    out, depth = [], 0
    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            info = line.lstrip()[3:].strip()
            depth += 1 if (info and depth == 0) else (-1 if not info else 0)
            depth = max(depth, 0)
            out.append("")
            continue
        out.append("" if depth else line)
    return "\n".join(out)


def last_section(text: str) -> str | None:
    """Номер последней секции документа — ТОЛЬКО вне фенсов.

    Наивная регулярка читает `## 99.` из шаблона внутри блока и объявляет, что
    ярлык «§0–§13» не покрывает §99. Это третий потребитель свойства «видит ли
    парсер фенс» в этом файле — два других (`blocks`, `section_order`) уже чинили
    по обеим осям (lab-11). Поймано собственным тестом сьюта, а не полем.
    """
    depth, best = 0, None
    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            info = line.lstrip()[3:].strip()
            depth += 1 if (info and depth == 0) else (-1 if not info else 0)
            depth = max(depth, 0)
            continue
        if depth:
            continue
        m = re.match(r"#{2,3}\s+(\d+)\.", line)
        if m and (best is None or int(m.group(1)) > int(best)):
            best = m.group(1)
    return best


def measure(text: str) -> tuple[int, int, int]:
    """→ (всего строк, строк канона, строк payload). Нет баннера → payload 0."""
    lines = text.splitlines()
    m = BANNER.search(text)
    if not m:
        return len(lines), len(lines), 0
    at = text[:m.start()].count("\n") + 1
    return len(lines), at - 1, len(lines) - at + 1


def _off(declared: int, actual: int) -> bool:
    """Разошлось ли объявление с фактом больше допуска."""
    if actual <= 0:
        return declared > 0
    return abs(declared - actual) / actual > TOLERANCE


def _say(where: str, what: str, declared, actual) -> str:
    ratio = f", ×{max(declared, actual) / max(1, min(declared, actual)):.1f}"
    return (f"{where}: объявлено {what} {declared}, измерено {actual}{ratio} — "
            "стоимость чтения врёт, а по ней решают, что не открывать")


def check_file(name: str, text: str) -> list[str]:
    """Объявления ФАЙЛА о себе: баннер и проза «Стоимость чтения»."""
    out: list[str] = []
    total, canon, payload = measure(text)
    text = outside_fences(text)   # примеры внутри блоков — не объявления файла
    m = BANNER.search(text)
    if m:
        at = text[:m.start()].count("\n") + 1
        claim = BANNER_CLAIM.search(m.group(1))
        if claim and _off(int(claim.group(1)), at):
            out.append(_say(f"{name} баннер payload", "начало payload",
                            int(claim.group(1)), at))
        pct = PERCENT.search(m.group(1))
        if pct and total and _off(int(pct.group(1)), round(payload * 100 / total)):
            out.append(_say(f"{name} баннер payload", "долю payload, %",
                            int(pct.group(1)), round(payload * 100 / total)))
    para = cost_paragraph(text)   # объявления файла о себе живут ЗДЕСЬ
    prose_c = PROSE_CANON.search(para)
    if prose_c and _off(int(prose_c.group(1)), canon):
        out.append(_say(f"{name} §0 «Стоимость чтения»", "канон",
                        int(prose_c.group(1)), canon))
    prose_p = PROSE_PAYLOAD.search(para)
    if prose_p and _off(int(prose_p.group(1)), payload):
        out.append(_say(f"{name} §0 «Стоимость чтения»", "payload",
                        int(prose_p.group(1)), payload))
    elif prose_p is None and payload and para:
        out.append(f"{name} §0 «Стоимость чтения»: размер payload не объявлен "
                   "числом при живом payload — сверять нечего, и молчание тише "
                   "протухшего объявления")
    return out


def check_map(map_text: str, sizes: dict[str, tuple[int, int, int]],
              last_sections: dict[str, str]) -> list[str]:
    """Таблица размеров в карте: числа против факта, ярлык против последней секции."""
    out: list[str] = []
    for layer, canon_s, payload_s in TABLE_ROW.findall(map_text):
        name = LAYER_FILE.get(layer)
        if name not in sizes:
            continue
        _, canon, payload = sizes[name]
        if _off(int(canon_s), canon):
            out.append(_say(f"карта, строка {layer}", "канон", int(canon_s), canon))
        if _off(int(payload_s), payload):
            out.append(_say(f"карта, строка {layer}", "payload",
                            int(payload_s), payload))
    for layer, upto in TABLE_LABEL.findall(map_text):
        name = LAYER_FILE.get(layer)
        last = last_sections.get(name)
        if last and int(upto) < int(last):
            out.append(f"карта, строка {layer}: ярлык §…–§{upto} не покрывает §{last} — "
                       "раздел есть, а в бюджет чтения не входит")
    return out
