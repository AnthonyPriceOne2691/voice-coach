# Tasks: soft-skills

Порядок — vertical slice. Каждая задача оставляет дерево зелёным.

- [ ] **T1. Класс вопроса и второй банк.** `Question.kind`; `load_bank` читает
      ключ `kind:` файла; `data/questions/behavioral.yaml` — 8 вопросов под профиль.
      Тесты: класс доезжает из файла; дефолт `technical` для старого банка.

- [ ] **T2. Чередование пула.** `pick_session_pool` принимает два списка и
      собирает T, S, T, S, T, S. Тесты: S1 (3 и 3), S2 (никаких двух подряд
      одного класса, первый — `first: true`).

- [ ] **T3. Политика follow-up по классу.** Ветка в `_may_follow_up`: technical —
      цифра, behavioral — эпизод и исход. Тесты: S3 (общий ответ → допрос),
      S4 (эпизод с исходом → нет допроса), S5 (тот же текст на техническом
      вопросе → допрос: правило не поехало).

- [ ] **T4. Инструкция и seed для behavioral follow-up.** Ветка в `_plan`.
      Тест: S6 — в инструкции есть действия/роль/исход и нет trade-off и
      измеримого эффекта.

- [ ] **T5. Имя режима и транскрипт.** `interview_mode = technical_and_behavioral`;
      класс вопроса виден в транскрипте. Тесты: S7, S8.

- [ ] **T6. Контракт не режет behavioral.** Тест: каждый seed нового банка и
      behavioral-инструкция проходят `interview.contract.yaml`; красная сторона
      проверена (L25).

- [ ] **T7. Канон.** doc 04 (банк, чередование, ветка политики), doc 01 (FR-2.5),
      doc 12 (`interview_mode`); concept `orchestrator-owns-structure.md` + `log.md`.

- [ ] **T8. Гейты.** `./scripts/run_checks.sh`; jscpd до и после (L30);
      diff-coverage локально с `LINT_PY_SRC=backend/app LINT_COV_PKG=app` (L32);
      `npm test` — фронт не тронут, и это замер.

- [ ] **T9. Живая сессия (S9).** Настоящий разговор: behavioral-вопрос задан,
      звучит естественно, ответ не ломает контракт. Результат — в verify-report.

- [ ] **T10. Handoff.** verify-report, decisions, метрики, `merge_guard.sh`,
      архив + строка в `delivery/archive/INDEX.md`.
