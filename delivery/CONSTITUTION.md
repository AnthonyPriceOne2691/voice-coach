# Delivery constitution

**Version:** 1.0
**Ratified:** 2026-07-28
**Canon stack:** delivery@1.99 · cqg@2.50 · okf@1.19
<!-- каноны вендорятся в docs/canon/ (AGENT_STACK.md §7.1, вариант C) -->
**CI:** deployed (github-actions) merge-gate: tooling   <!-- §10.4 -->

## Non-negotiables

- Done закрывается **зелёным CI-прогоном** (§10.4), не локальным «у меня прошло».
- `STRICT=0` / `git commit -n` — аварийная локальная мера, видимая в PR; в CI запрещены.

## Process principles

1. Spec before broad implementation (class M/L).
2. Vertical slices; no oneshot of the whole plan.
3. Done = oracles (shape + behavior + product), never self-declaration alone.
4. Builder ≠ Verifier.
5. Agent mistake → strengthen harness (oracle / breaker / hook), not only prompts.
6. One `delivery/active` at a time.

## Project-specific (Voice Interview Coach)

Эти пункты — про **процесс** этого продукта. Пороги lint/типов сюда не пишутся
(они в CQG), дизайн-решения — тоже (они в `docs/00–20`).

7. **`docs/00–20` — канон дизайна и вход в любую задачу.** Не переизобретать
   решения оттуда; расхождение кода с доком чинится в том же PR (либо код, либо док).
8. **Транскрипт — единственный невосполнимый артефакт.** Любая правка voice-цикла
   обязана сохранить flush при каждом turn; падение хода — recoverable, не фатально.
9. **Latency — продуктовое требование, а не оптимизация.** Sentence-streaming в
   TTS не разбирать: буферизация полного ответа проваливает гейт (4.8 s vs 3.0 s).
10. **D-8 закрыт:** весь voice-цикл — `qwen2.5:14b-instruct`; `deepseek-r1:14b`
    только offline summary. Возврат R1 в voice-цикл = смена инварианта → spec + human OK.
11. **Реальные AI всегда мокаются в тестах.** Живой прогон (ollama/whisper/piper) —
    ручной smoke, он не в CI и не заменяет тесты.
12. **HITL на приватных данных:** `data/sessions/**` — транскрипты пользователя,
    gitignored. Не коммитить, не отправлять наружу, не класть в отчёты.

## Coding-agent contract (thin ABC)

### Preconditions
- STATUS.md read; class S/M/L known; branch/worktree set.
- Before implement: artifacts per harness §2.2 (S: tasks; M/L: spec+plan+tasks + human_ok_spec).
- Прочитан релевантный `docs/NN-*.md` — канон дизайна первичен по отношению к коду.

### Invariants
- No secrets in git; no force-push to main; no done-on-red; no silent scope creep.
- ≤ 500 LOC на файл; AI-интеграции только за Protocols (`SpeechToText`, `TextToSpeech`,
  `LlmClient`); промпты и контракты — в `data/`, не в коде (enforced: CQG).

### Governance
- Human OK on spec (M/L). Human OK on plan (L / risky). HITL on prod deploy, data migrations, security-sensitive changes.
- HITL на всё, что трогает `data/sessions/**` или отправляет данные из машины наружу.

### Recovery
- On oracle red: fix ≤ retry budget, else escalate in STATUS.md.

## Pointers to sibling layers (fill if deployed)

- Code shape oracles: `CODE_QUALITY_GATES.md` (vendored: `docs/canon/`) — [x] deployed
- Domain canon: `OKF_KNOWLEDGE_BUNDLE.md` / `knowledge/` (vendored: `docs/canon/`) — [x] deployed
- Agent hooks (§10): [x] deployed (`scripts/hooks/`, см. `delivery/README.md`)
- CI oracles (§10.4, workflow per CQG §8): [x] deployed
- Skills catalog: `skills/README.md` — [x] absent (нет длинных inline-промптов в коде;
  промпты живут в `data/prompts/`, что закрывает роль каталога для этого проекта)

## Где что лежит

| Слой | Путь |
|---|---|
| Карта стека | `docs/canon/AGENT_STACK.md` (upstream: `Prepare/`, не коммитится) |
| Приёмка стека | `delivery/STACK-ACCEPTANCE.md` |
| Канон дизайна продукта | `docs/00–20` |
| Канон домена (OKF) | `knowledge/` |
| Гейты кода | `.pre-commit-config.yaml` + `scripts/lint/` |
| Гейт мержа | `scripts/merge_guard.sh` + `.git/hooks/pre-push` |

## Agent permissions

Границы действий агента. Правило: **необратимое — `deny`, обратимое, но платит
человек временем — `ask`.** Подтверждение на необратимом — не защита, а соучастие.

`allow` здесь не перечисляется: это накопительный список конкретных команд, его
место только в `.claude/settings.json` (§4.5). Строки ниже обязаны совпадать с
файлом настроек: объявить здесь и не положить в настройки — значит, что гейт прав,
а развёртывание нет.

```text
agent-permissions
# Необратимое: подтверждение здесь не защита, а соучастие.
deny: Bash(git push --force:*)
deny: Bash(git push:* --force-with-lease)
deny: Bash(rm -rf /:*)
deny: Bash(psql:*)
deny: Bash(mysql:*)
deny: Read(./.env)
deny: Read(./**/.env)
# Обратимо, но платит человек своим временем.
ask: Bash(git push:*)
ask: Bash(gh pr merge:*)
ask: Bash(pip install:*)
ask: Bash(npm install:*)
ask: Bash(uv sync:*)
ask: WebFetch
```

<!-- `uv sync` добавлен против шаблона канона осознанно: в этом проекте
     зависимости ставит именно он, а не pip/npm — иначе строка `ask` про установку
     пакетов не покрывала бы фактический способ установки. -->
