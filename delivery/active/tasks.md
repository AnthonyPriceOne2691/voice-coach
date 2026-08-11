# Tasks

- [x] T1. Worktree `contour/2.01` от `main`; дерево `main` не трогается
- [x] T2. Извлекатель payload'а по трём правилам §5.0 (первый фенс после
      заголовка · счёт глубины фенсов · фенс с отступом); сверка с
      `stack_selftest`: 97 блоков, извлечено 73/73 файла
- [x] T3. Новый `contour_doctor.py` + 7 частей — **первым**, иначе шаг 2 §5.5 молчит
- [x] T4. Природа расхождений: сверка проекта со снимком `docs/canon@1.61`.
      17 «разошедшихся» скриптов = устарели (перезаписать), 5 конфигов =
      адаптированы (портировать), 1 файл совпал с каноном обеих версий
- [x] T5. 28 отсутствующих файлов payload'а: 11 частей фазового гейта, 7 частей
      доктора, половины mutation/complexity/ast/gate-coverage/dependency,
      `check_layers_gate.sh`, `.dependency-cruiser.cjs`
- [x] T6. Подстановка роли: `import-linter` -> `layers-gate` в конфиге (роль одна,
      порог один; теперь её видит мета-гейт)
- [x] T7. Портирование канонной дельты в `.pre-commit-config.yaml` (mypy по
      кандидатам venv, сообщения secrets), `quality.yml` (actions@v7, вычисляемый
      `cache:`, шаг «Инструменты гейтов на месте», `--verbose`, `if: always()`)
- [x] T8. `adapted.json` / `canaries.json` / `not-applicable.json`
- [x] T9. Сужение env-префикса у grep/ast/file-length: лишний `LINT_BE_DIR`
      делал знаменателем области весь `backend`, включая `backend/tests`, —
      маска гейта их не покрывает никогда, и доктор звал это `DEAD`
- [x] T10. `backend/pyproject.toml`: снято `readme = "../README.md"` — на чистом
      дереве `uv sync` падал, то есть гейты не стартовали
- [x] T11. Перевендоривание снимка + обе части селфтеста + `SHA256SUMS`
- [x] T12. Три записи о версии -> `delivery@1.68 · cqg@2.01 · okf@1.15`
- [x] T13. Архив `contour-bootstrap-1.61` + `observed.md` (§13) + строка в `INDEX.md`
- [x] T14. `STACK-ACCEPTANCE.md`: карта ролей, `checked_at`/`stale_after`, остатки
- [x] T15. Решением человека (2026-08-11) вместо waiver'а починен код: 4 функции
      фронта разделены, non-null assertion в `main.tsx` заменён проверкой,
      6-строчный дубль History/Words вынесен в `ListState`; снимки сложности и
      DRY вернулись к дореформенным значениям, ратчет зелёный без легализации
- [x] T16. Решением человека поставлен `dependency-cruiser`: TS-половина гейта
      слоёв судит (21 модуль), контракты фронта проверены воспроизведением
- [x] T17. Приёмка: `pre-commit` 28/28, три вопроса §5.5, `pytest` 91/93.79%,
      smoke 6/6, frontend build + 14 тестов; результаты — в `verify-report.md`
- [ ] T18. Зелёный прогон `quality` в CI на ветке; push, PR и мерж — ход человека
      (`git push -u origin contour/2.01` → PR → `scripts/merge_guard.sh`)
