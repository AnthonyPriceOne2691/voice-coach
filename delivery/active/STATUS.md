# Active delivery status

- **slug:** portfolio-knowledge
- **stack:** delivery@1.68, cqg@2.02, okf@1.15
- **class:** M
- **kind:** feature
- **repro_test:** n/a reason=не багфикс; предмет — содержимое знания агента, оракулы ниже проверяют бюджет токенов и покрытие проектов
- **diagnosis:** n/a reason=не багфикс, дефекта не было — знание просто не покрывало четыре проекта
- **phase:** implement
- **builder:** agent:claude-code
- **verifier:** human:anthony
- **human_ok_spec:** yes (by=human:anthony, at=2026-08-12) reason=примеры F1–F6 предъявлены ДО кода; человек выбрал вариант «цифры измеренные, а не из CV» и принял его цену — Генри может спросить про число, которого в текущем CV нет
- **human_ok_plan:** n/a
- **shape-oracles:** cqg-deployed
- **behavior-oracles:** tests-present
- **artifact_oracle:** n/a reason=правка данных и доков; фронт и сборка не затронуты
- **ci-oracles:** tooling
- **worktree:** ../voice-coach-portfolio (ветка feat/portfolio-knowledge)
- **hooks:** claude (scripts/hooks/)
- **blockers:** none
- **waivers:** none
- **new_dependency:** none reason=правка markdown в data/knowledge и docs; кода не добавляется
- **runtime_paths:** none reason=подумали и нет: знание попадает в промпт через уже существующий `{{profile_condensed}}`, путь исполняется каждым тестом ws и smoke-оракулом S6; отказ виден сборке и тестам, целевой среды сверх этого нет
- **canon_drift_waiver:** no
- **baseline_growth_waiver:** no
- **observability:** 1
- **observe_signal:** F1–F5 подтверждены; в живой сессии Генри задаёт вопрос про
  проект, отличный от LinkBuilder, и называет его цифру верно
- **observe_until:** 2026-08-26
- **circuit_breakers:** defaults from AGENT_DELIVERY_HARNESS.md §3.4

## Что это

Сегодня в системный промпт инжектится только `profile_condensed.md`
(`knowledge/prompts.py:35`), и в нём — LinkBuilder плюс упоминание Event Content
System. **Четырёх проектов портфолио агент не видит вовсе**: Voice Interview
Coach, Local Web Agent, Lash Try-On, SEO:Content Toolkit.

Цель: Генри знает кандидата так, будто перед ним лежит CV, и может спрашивать
про любой проект, а не про один.

**Слот `case study ≤ 1000 токенов` из doc 20 остаётся незаполненным** — это
осознанно: выбор, чей кейс подставить, принимает оркестратор, а он в этой
поставке не трогается (I1-H6: структурой владеет оркестратор). Здесь только
индекс, который влезает в бюджет профиля.
