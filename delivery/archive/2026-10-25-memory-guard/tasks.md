# Tasks: memory-guard

- [x] T1 — `orchestrator/tips.py`: `locate` и `latin_only` открыты для памяти, поведение
  заметок к речи прежнее (`test_tips_policy.py` без правок).
- [x] T2 — `data/contracts/memory.contract.yaml` (M-H1…M-H7 с числами) и
  `data/contracts/memory_never_store.txt` (шаблоны по шести категориям).
- [x] T3 — `memory/rules.py`: загрузка чисел и списка, громкие ошибки на кривых данных.
- [x] T4 — `memory/guard.py`: `parse_candidates`, `decide`, `sift`, журнал отказов без
  текста (K3–K8, K10, K12).
- [x] T5 — `backend/tests/test_memory_guard.py`: таблицы случаев и пять инвариантов на
  переборе; сторож маркеров `test_contracts.py` обобщён на контракт памяти.
- [x] T6 — слой `memory` в `backend/.importlinter`.
- [x] T7 — доки: doc 13, концепт `knowledge/ops/talk-memory.md`, `orchestrator-owns-structure`,
  `knowledge/index.md`, `knowledge/log.md`, `delivery/rule_enforcers.md`.
- [x] T8 — мутации, verify-report, handoff, PR и зелёные `CI`/`quality`. Уроки этой
  поставки, записанные на handoff, — L105, L106, L107 (`delivery/archive/INDEX.md`).
