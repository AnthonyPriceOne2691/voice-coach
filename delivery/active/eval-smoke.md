# Eval / smoke: talk-check-core

## Продуктовые оракулы этой поставки

| Пример | Оракул | Где | Статус |
|---|---|---|---|
| C1, C3, C4, C6, C7 | решение кода на настоящем контракте разговора | `backend/tests/test_tips_policy.py` | ✅ на каждом прогоне |
| C5 | одна заметка об ошибке из смешанной реплики | `test_tips_policy.py::test_mixed_utterance_gives_one_note_about_the_error` | ✅ |
| C6 (свойство) | фрагмент заметки — всегда дословный кусок реплики; несказанное не отмечается | `test_tips_policy.py`, hypothesis | ✅ |
| C8 | префикс разговора не тронут, просьба последней, схема и `num_ctx` клиента | `test_language_check.py`, `test_ollama_client.py` | ✅ |
| C8 (живой) | первый токен хода после проверки — без полного prefill | `delivery/evals/talk-check/run.py --latency` | по «запускай» |
| C9 | eval 37 случаев в шести классах, пороги спеки | `delivery/evals/talk-check/run.py` | по «запускай» |

## Smoke

`delivery/evals/smoke/run.sh` — без изменений: ядро не входит в путь хода (его подключает
talk-check-wiring), поэтому смоук продукта не меняется.
