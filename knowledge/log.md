# Knowledge Bundle Update Log

## 2026-08-12 — темп речи по голосовой просьбе

* **Orchestrator owns structure**: инвариант расширен — **что считать ответом**
  тоже структура. Просьба сменить темп распознаётся детерминированно
  (`orchestrator/pace.py`) и обрабатывается мета-ходом, не двигая машину
  состояний. `implementation:` пополнен `pace.py`.
* **Sentence streaming**: темп синтеза объявлен параметром **каждого** вызова, а
  не константой процесса; носитель — `voice/tts_paced.py` (добавлен в
  `implementation:`). Записано требование перезамера latency-гейта при любом
  расширении коридора темпа.
* **Границы**: `docs/04`, `12`, `15`, `17` обновлены в том же изменении —
  мета-ход, значение `state: PACE_REQUEST` и ключ `speech_length_scale`.

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
