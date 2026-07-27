# Knowledge Bundle Update Log

## 2026-07-28

* **Initialization**: создан OKF v0.2 bundle (`knowledge/`) при развёртывании канон-стека.
* **Preflight**: upstream SPEC сверен по
  https://raw.githubusercontent.com/GoogleCloudPlatform/knowledge-catalog/main/okf/SPEC.md —
  версия upstream `0.2` совпадает с pinned `0.2` в `OKF_KNOWLEDGE_BUNDLE.md` §0.1.
  Расхождений, требующих правки канона, не найдено.
* **Creation**: seed-concept'ы под `product/`, `engineering/`, `ops/`, `references/` —
  шесть инвариантов, которые агент чаще всего нарушает (см. `index.md`).
* **Scope**: `docs/00–20` big-bang не переносились — остаются каноном дизайна,
  bundle фиксирует поверх них машинопроверяемые инварианты (`implementation:`).
