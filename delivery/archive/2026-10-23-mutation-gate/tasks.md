# Tasks: мутационный гейт судит (mutation-gate)

- [x] W1. Воспроизвести «не просудил» на диффе talk-screen; журнал гипотез — `diagnosis.md`
- [x] W2. Тесты M1–M4 (`test_repo_root.py`) и M5 (`test_mutation_copy.py`) — до правки красные
- [x] W3. Корень по данным в `app/config.py`; тринадцать тестовых файлов берут корень из `app.config`
- [x] W4. Отложенные аннотации в `vocabulary.py`; `--no-cov` в `[tool.mutmut]`
- [x] W5. `TurnEnforcer` без `@dataclass` — гейт видит проверки контракта (M12)
- [x] W6. Тесты прогрева M8–M10 (`test_warmup.py`); обратный прогон M7
- [x] W7. Замер долей M11 по модулям на свежем `mutants/`; выжившие — разбор
- [x] W8. Канонный шаг мутаций в `quality.yml`; `adapted.json`; «Остатки 2.69» в STACK-ACCEPTANCE
- [x] W9. PR, CI: шаг судит дифф PR (M13) — прочитать лог шага
- [x] W10. `eval-smoke.md`, `verify-report.md`, метрики; STATUS → verify
- [x] W11. Слияние `origin/main` (talk-check-core) — шаг мутаций в CI «не просудил»: два новых теста считали корень `parents[2]`; сторож M15 на класс, правка двух файлов
