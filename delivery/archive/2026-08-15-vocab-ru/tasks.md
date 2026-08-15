# Tasks: `translation_ru` обязан быть русским

- [x] **T1. Repro-тест** — запись из живой базы (`выразительный陳述`) не проходит
      проверку; `автоматизация outreach` проходит (V1, V2, V3). Красный до правки.
- [x] **T2. Предикат** в `summary/validate.py`: `translation_is_russian` +
      `translation_problem` (причина словами для лога).
- [x] **T3. Контракт** — `S-H6_translation_is_russian` в
      `data/contracts/summary.contract.yaml`, поле названо явно.
- [x] **T4. Починка** в `_generate_validated` (одно место на оба пути) +
      `data/prompts/translate_term_system.txt`; тесты V4, V5, V6, V7 на
      `ScriptedLlm`.
- [x] **T5. Сторожа контракта** — тест A (id ↔ маркер в коде) и тест B
      (`exclude_fields` покрыто другим инвариантом), V8.
- [x] **T6. Промпт** `summary_system.txt` — прямой запрет иероглифов (вторая линия).
- [x] **T7. Скрипт чистки** `scripts/repair_vocabulary.py`: dry-run по умолчанию,
      `--apply` чинит, ничего не удаляет. Прогнать на копии базы, потом на живой.
- [x] **T8. Канон** — doc 08 (правило про `translation_ru`),
      `knowledge/engineering/model-split.md` (починка идёт на qwen, не на R1;
      `implementation:` уже содержит `summary/service.py`).
- [x] **T9. Verify** — `run_checks.sh`, гейты контура, `eval-smoke.md`,
      `verify-report.md`; живой прогон скрипта на банке.
