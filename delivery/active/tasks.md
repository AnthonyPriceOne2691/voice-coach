# Tasks: talk-tips

- [ ] T1 — контракты: запрещённые фразы по правилу (cherry-pick 72a2f7b) и тест на
  два правила `forbid_patterns` в одном контракте.
- [ ] T2 — правило `I3-H4_no_corrections` и `talk_corrections_forbidden.txt`; тесты
  контракта (C16): поправки режутся, беседа и причины проходят.
- [ ] T3 — шаблоны `tips:` в `data/talk/talk.yaml`, `TalkScript.tips`; тест: шаблон —
  английский без оценок, и его ловит I3-H4.
- [ ] T4 — `voice/talk_tips.py` (`PlaybackClock`, `tip_line`, `TalkTips`) и
  `TalkChecks.note_by`; модульные тесты срока (C17).
- [ ] T5 — `TalkFlow.on_tip` (`state: TIP`, `spoken: true`, мимо истории модели);
  `last_agent_text` пропускает подсказку.
- [ ] T6 — проводка в `ws_voice.py`; `PACE_SETTING` и шаблоны темпа — в `pace.py`;
  WS-тесты C14–C17 и канарейка.
- [ ] T7 — doc 12, 13, 15; `rule_enforcers.md`; концепты `knowledge/` и `log.md`.
- [ ] T8 — verify, handoff.
