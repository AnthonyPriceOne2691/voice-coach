// Разбор (debrief) — к той форме, которую рисует SummaryCard (схема doc 08).
//
// Разбор пишет LLM, и форма его полей-списков — обещание модели, а не факт.
// Живая запись от 2026-07-05 хранит `next_session_focus` ОДНОЙ строкой (подсказка
// модели говорила `[string]`): NextFocus звал у неё `.join`, React ронял всё
// дерево, и History → Open давал пустую страницу. С 2026-09-29 бэкенд приводит
// поля-списки при разборе (`backend/app/summary/validate.py`), но записи,
// сохранённые раньше, так и лежат в базе. Поэтому фронт приводит их сам — здесь,
// в одном месте и по тем же правилам: строка на месте списка строк — список из
// неё; голая строка на месте объекта — объект с главным текстовым полем; прочий
// мусор выбрасывается.

import type { Debrief, VocabularyItem } from "../types/api";

type Strength = NonNullable<Debrief["strengths"]>[number];
type Improvement = NonNullable<Debrief["improvements"]>[number];
type WeakAnswer = NonNullable<Debrief["weak_answers"]>[number];

function asItems(value: unknown): unknown[] {
  if (value === null || value === undefined) return [];
  return Array.isArray(value) ? value : [value];
}

function isText(item: unknown): item is string {
  return typeof item === "string" && item.trim() !== "";
}

/** Список непустых строк: строка — список из неё, нестроковое выброшено. */
function asStringList(value: unknown): string[] {
  return asItems(value)
    .filter(isText)
    .map((item) => item.trim());
}

/** Список объектов: объект — список из него; строка — объект с полем `textKey`. */
function asObjectList<T extends object>(value: unknown, textKey?: keyof T & string): T[] {
  return asItems(value).flatMap((item): T[] => {
    if (typeof item === "object" && item !== null && !Array.isArray(item)) return [item as T];
    if (textKey && isText(item)) return [{ [textKey]: item.trim() } as T];
    return [];
  });
}

export function normalizeDebrief(debrief: Debrief): Debrief {
  return {
    ...debrief,
    strengths: asObjectList<Strength>(debrief.strengths, "text"),
    improvements: asObjectList<Improvement>(debrief.improvements, "problem"),
    weak_answers: asObjectList<WeakAnswer>(debrief.weak_answers, "question"),
    // Запись словаря — три обязательных поля (S-H4): строкой ей не стать.
    vocabulary: asObjectList<VocabularyItem>(debrief.vocabulary),
    consistency_flags: asStringList(debrief.consistency_flags),
    next_session_focus: asStringList(debrief.next_session_focus),
  };
}
