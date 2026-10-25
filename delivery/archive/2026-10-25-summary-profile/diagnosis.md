# Diagnosis: сводка ставит `positioning`, не видя профиля кандидата

**Симптом.** Оба промпта офлайн-разбора объявляют профиль входом:
`summary_system.txt` — «INPUT … Candidate profile» и правило о позиционировании,
`minimal_summary_system.txt` — «INPUT: interview transcript + candidate profile only.»
Оба требуют балл `positioning` 1–5. Найдено сторонним агентом чтением кода,
подтверждено ведущей сессией по коду `main`.

## Воспроизведение — сначала оно

Репро — `backend/tests/test_summary.py::test_full_summary_sends_the_candidate_profile`
и его пара для минимальной сводки: НАСТОЯЩИЕ промпты сводки из `data/prompts/`,
синтетический профиль во временном `profile_condensed.md`, фейковая модель
`ScriptedLlm` записывает сообщения вызова. На `main` `5d7d7b7`:

```
E       AssertionError: профиль не дошёл до сводки
E       assert '# Candidate Profile\n\nSam Example - builds AI pipelines …' in
        'You produce a structured post-session summary in JSON only.\n\nINPUT\n- Interview
        transcript\n- Review transcript (if...lead vs AI automation engineer.\n\nOUTPUT…'
FAILED tests/test_summary.py::test_full_summary_sends_the_candidate_profile
FAILED tests/test_summary.py::test_minimal_summary_sends_the_candidate_profile
FAILED tests/test_summary.py::test_summary_without_profile_file_says_so[full]
FAILED tests/test_summary.py::test_summary_without_profile_file_says_so[minimal]
4 failed, 18 passed
```

Красный по правильной причине: модель получает системный промпт ровно как файл, без
профиля и без заглушки; падение — на утверждении о профиле, а не раньше (роль
первого сообщения — `system`, утверждение до него проходит).

## Журнал гипотез

| # | Гипотеза | Как проверял | Вердикт |
|---|---|---|---|
| H1 | Профиль доходит, но в `user`-сообщении, а не в системном | репро собирает ВСЕ сообщения вызова; текста профиля и заглушки нет ни в одном | ОПРОВЕРГНУТА |
| H2 | Профиль подставляет сам сервис сводки, другим путём | `grep -n profile backend/app/summary/` — ни одного упоминания; `generate_full`/`generate_minimal` берут `system` из `PromptLibrary.system()`, `user` = `SCHEMA_HINT` + транскрипты | ОПРОВЕРГНУТА |
| H3 | Объявление входа без исполнителя: `system()` отдаёт файл как есть, а в промптах сводки нет плейсхолдера `{{profile_condensed}}` | в обоих файлах плейсхолдера нет; `system()` не зовёт `_profile()`; докстринг «summary passes inject their own context» обещает подстановку, которой нет ни в одном вызывающем | ПОДТВЕРЖДЕНА |
| H4 | Дефект регрессия, а не врождённый | `git log`: промпт с «Candidate profile» — `00233bf` (2026-07-02), `system()` с докстрингом «raw» и сервис сводки — `f604621` (2026-07-05); с тех пор профиль в сводку не шёл ни разу — 112 дней | ОПРОВЕРГНУТА — врождённый |
| H5 | Правило позиционирования верно, не хватает только профиля | роль в правиле — «SEO lead vs AI automation engineer»; профиль с `f5a20db` (2026-10-17) — AI Delivery Lead, таблица `Positioning rules` в нём своя | ОПРОВЕРГНУТА — правило тоже устарело, и без профиля его не с чем сверить |

## Почему не поймал ни один гейт

Все тесты сводки (`test_summary.py`) строят `PromptLibrary` на временных промптах
вида `"summary system"` — настоящие файлы промптов сводки в них не участвовали, и
вопроса «что модель получает на самом деле» не задавал никто. Это L20 на новом
пути: проверялся сервис, а не собранный промпт. Сторож `test_real_repo_prompts_load`
стоял только на промпте интервью.
