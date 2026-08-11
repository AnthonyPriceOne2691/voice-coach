# Eval smoke — this shipment

Derived from spec acceptance (A1–A7). Run during verify.

Предмет этой поставки — сами инструменты контура, поэтому её smoke — прогоны
инструментов, а не живой voice-цикл. Продуктовые оракулы
(`delivery/evals/smoke/run.sh`) всё равно обязаны остаться зелёными: контур не
имеет права изменить поведение продукта, и это проверяется, а не предполагается.

## Оракулы контура (механические, воспроизводимые)

- [ ] **A1** `python3 scripts/lint/contour_doctor.py` -> `DEAD 0`
- [ ] **A2** `python3 docs/canon/stack_selftest.py docs/canon` -> `98 block(s), 0 failure(s)`
- [ ] **A3** `bash scripts/lint/check_gate_coverage.sh` -> `gate-coverage: OK`,
      подключено >= 12, у каждого неподключённого напечатана причина
- [ ] **A4** `bash scripts/lint/check_layers_gate.sh` -> судят ОБЕ половины
      (`dependency-cruiser` поставлен решением человека); ноль модулей у TS-половины
      обёртка обязана уронить, а не зачесть
- [ ] **A5** `python3 scripts/delivery_check.py --require-ci` -> 0 ошибок
- [ ] **A6** части комплектов на месте: 9 x `scripts/lint/doctor_*.py`,
      11 x `scripts/delivery_*.py` (без части вход не стартует вовсе)
- [ ] **A7** версии в `docs/canon/*.md` == `stack:` в `STATUS.md` == `CONSTITUTION.md`.
      На `cqg@2.02` это уже МЕХАНИКА, а не чтение: `doctor_versions.py` печатает
      «N записей согласны» по каждому слою и называет адреса при расхождении
- [ ] `bash scripts/lint/check_canon_vendor.sh` -> манифест сходится, селфтест
      на копии проходит (комплект из двух файлов лежит и в снимке)
- [ ] `pre-commit run --all-files --verbose` -> зелено, и каждый сканирующий гейт
      печатает НЕПУСТОЕ число просмотренного (§6: «чисто» != «ноль файлов»)

## Продуктовые оракулы (не должны шелохнуться)

- [ ] `bash delivery/evals/smoke/run.sh` — зелено
- [ ] `cd backend && uv run pytest` — проходит, покрытие не ниже гейта 85%
- [ ] `cd frontend && npm run build && npm test` — проходит

## Живой прогон (ручной, вне CI — constitution §11)

Не требуется: поставка не трогает ни `backend/app/**`, ни `frontend/src/**`.
Строка стоит здесь именно поэтому — «не проверяли» и «нечего проверять» обязаны
различаться в тексте, а не в тишине.
