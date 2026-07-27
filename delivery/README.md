# Delivery contour

Phased AI delivery harness. See vendored canon `docs/canon/AGENT_DELIVERY_HARNESS.md`.

- `CONSTITUTION.md` — process principles + thin coding-agent contract
- `active/` — current shipment only
- `archive/` — finished shipments
- `evals/smoke/` — durable product smoke oracles
- `STACK-ACCEPTANCE.md` — приёмка самого стека (§6 карты) + разбор её слепых пятен

## Команды

```bash
python3 scripts/delivery_check.py                          # артефакты фазы
python3 scripts/delivery_check.py --diff-base origin/main  # + circuit breakers §3.4
python3 scripts/delivery_metrics.py --base origin/main --write   # метрики на handoff
bash delivery/evals/smoke/run.sh                           # product oracles
```

## Agent hooks

`scripts/hooks/stop_on_red.sh` — не давать объявить done на красном.
`scripts/hooks/protect_main.sh` — блокировать force-push в main.
Подключение зависит от IDE (Delivery §10 / A.11); контракт поведения — в каноне.
