"""Summary JSON validation — summary.contract.yaml hard rules as code."""

import json
import re
from typing import Any

SCORE_KEYS = ("clarity", "structure", "technical_depth", "english_fluency", "positioning")

CYRILLIC = re.compile(r"[Ѐ-ӿ]")
#: Иероглифы, кана и хангыль. `deepseek-r1:14b` — мультиязычная модель, и на
#: длинной генерации она срывается на китайский: в банке слов из-за этого лежит
#: `выразительный陳述`. Ловим весь блок, а не один язык: срыв бывает и в японский.
CJK = re.compile(r"[぀-ヿ㐀-䶿一-鿿가-힯豈-﫿]")

#: Поля-списки схемы `summary_output` (doc 08). Их форма — обещание модели, а не
#: факт: на подсказку `next_session_focus [string]` R1 вернул ОДНУ строку, фронт
#: позвал у неё `.join`, и экран History → Open → Summary падал пустой страницей.
#: Поэтому форма приводится здесь, до записи в БД, а не там, где её читают.
STRING_LIST_FIELDS = ("consistency_flags", "next_session_focus")
#: Списки объектов → поле, которым становится голая строка на месте объекта.
#: Строку не выбрасываем: это текст модели, и его пропажа была бы молчаливой.
#: `vocabulary` здесь нет — у записи словаря три обязательных поля (S-H4), и
#: строка ими стать не может.
OBJECT_LIST_TEXT_KEYS = {"strengths": "text", "improvements": "problem", "weak_answers": "question"}


def translation_problem(text: str) -> str | None:
    """Почему перевод не годится — словами, для лога. `None` = годится (S-H6).

    Латиница НЕ запрещена: `автоматизация outreach` законна, `Redis` в переводе
    термина `Redis` — тоже. Требуем ровно двух вещей: кириллица есть, иероглифов
    нет. Более строгое правило дало бы ложные срабатывания на каждой второй
    записи, а это дороже пропуска (Delivery §4.3b).
    """
    if CJK.search(text):
        return "содержит иероглифы"
    if not CYRILLIC.search(text):
        return "нет ни одной кириллической буквы"
    return None


def translation_is_russian(text: str) -> bool:
    """S-H6: перевод обязан быть русским.

    Поле `vocabulary.translation_ru` ИСКЛЮЧЕНО из `S-H2_en_body` (там английский),
    и до этой проверки его не покрывало ничто: исключение из одного правила молча
    стало «может быть чем угодно».
    """
    return translation_problem(text) is None


class SummaryInvalidError(ValueError):
    """LLM output failed the summary contract; message is the retry hint."""


def extract_json(raw: str) -> dict[str, Any]:
    """S-H1: разбор первого блока {...} (модели любят обернуть JSON в прозу и фенсы).

    Здесь же исполняется S-H5: пустой после `strip_thinking` ответ — это ответ без
    JSON, и он отвергается той же ошибкой. Разделять их незачем: у R1 «пусто после
    снятия рассуждений» и «нет JSON» — одно и то же событие.
    """
    start, end = raw.find("{"), raw.rfind("}")
    if start == -1 or end <= start:  # S-H1 + S-H5_nonempty_after_strip
        raise SummaryInvalidError("no JSON object found in output")
    try:
        data = json.loads(raw[start : end + 1])
    except json.JSONDecodeError as exc:
        raise SummaryInvalidError(f"invalid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise SummaryInvalidError("top-level JSON value must be an object")
    return data


def _as_items(value: object) -> list[object]:
    """Одиночное значение — список из него, `None` — пустой список."""
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def _string_list(value: object) -> list[str]:
    """S-H1: список непустых строк. Строка → [строка], нестроковое выбрасывается."""
    return [item.strip() for item in _as_items(value) if isinstance(item, str) and item.strip()]


def _object_list(value: object, *, text_key: str | None = None) -> list[dict[str, Any]]:
    """S-H1: список объектов. Объект → [объект], строка → `{text_key: строка}`."""
    shaped: list[dict[str, Any]] = []
    for item in _as_items(value):
        if isinstance(item, dict):
            shaped.append(item)
        elif text_key and isinstance(item, str) and item.strip():
            shaped.append({text_key: item.strip()})
    return shaped


def _shape_list_fields(data: dict[str, Any]) -> None:
    """Поле-список схемы — всегда список, что бы ни прислала модель (S-H1).

    Нет поля или `null` — пустой список: фронт рисует секцию только когда в ней
    что-то есть, а отсутствие ключа и `[]` для него одно и то же.
    """
    for field in STRING_LIST_FIELDS:
        data[field] = _string_list(data.get(field))
    for field, text_key in OBJECT_LIST_TEXT_KEYS.items():
        data[field] = _object_list(data.get(field), text_key=text_key)


def validate_summary(data: dict[str, Any], *, require_vocabulary: bool) -> dict[str, Any]:
    scores = data.get("scores")
    if not isinstance(scores, dict):
        raise SummaryInvalidError(
            f"missing scores object: got {type(scores).__name__}, "
            f"ключи верхнего уровня — {sorted(data)}"
        )
    for key in SCORE_KEYS:
        value = scores.get(key)
        if not isinstance(value, int) or not 1 <= value <= 5:  # S-H3
            raise SummaryInvalidError(f"scores.{key} must be an integer 1-5, got {value!r}")

    # Словарь приводится тем же правилом, что остальные поля-списки. Раньше `null`
    # на его месте у minimal-разбора (где словарь не обязателен) слал разбор на
    # повтор, а дважды подряд — оставлял сессию без разбора вовсе.
    complete = [
        item
        for item in _object_list(data.get("vocabulary"))
        if str(item.get("term_en", "")).strip()
        and str(item.get("translation_ru", "")).strip()  # S-H4 (FR-6.3)
        and str(item.get("example_en", "")).strip()
    ]
    if require_vocabulary and not complete:
        raise SummaryInvalidError(
            "vocabulary must contain items with term_en/translation_ru/example_en"
        )
    data["vocabulary"] = complete
    _shape_list_fields(data)

    for field in ("overall_summary",):
        if re.search(r"[Ѐ-ӿ]", str(data.get(field, ""))):  # S-H2: EN body fields
            raise SummaryInvalidError(f"{field} must be English")
    return data
