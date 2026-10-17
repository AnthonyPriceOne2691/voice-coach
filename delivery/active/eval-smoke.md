# Eval smoke — profile-refresh

Derived from spec acceptance (P1–P7). Run during verify, 2026-10-17.

## Оракулы поставки

- [x] **P1** нынешняя позиция и положение — `test_profile_states_current_position`;
      до правки красный: `профиль не говорит о нынешнем положении: 'AI Delivery Lead'`
- [x] **P2** десять проектов поимённо, у каждого цифра —
      `test_profile_covers_whole_portfolio`, `test_every_project_carries_a_number`;
      до правки красный: `проекты не видны агенту: ['SEO case-study platform',
      'Prospecting & outreach platform', 'G connect', 'RAG over a rulebook', 'Quality contour']`
- [x] **P3** устаревшие факты убраны, цифры на своих проектах —
      `test_profile_drops_stale_facts`; до правки красный: пять устаревших строк
- [x] **P4** бюджет и приватность — `test_profile_fits_token_budget` (5,089
      символов ≈ 1,272 токена из 1,500; было 5,468 ≈ 1,367), `test_profile_has_no_personal_contacts`,
      `test_profile_keeps_private_life_out`. Сторож личного зелёный и до правки
      (личного в профиле не было) — проверен мутациями: «daughter»/«wife» и
      «Smart frend Ally» в тексте → красный
- [x] **P5** зачем английский — `test_profile_says_why_spoken_english_matters`;
      до правки красный: `не названа причина учить английский: 'discovery calls'`
- [x] **P6** знание в собранных промптах интервью и разбора —
      `test_new_projects_reach_both_prompts`; до правки красный: `'G connect' не
      доехал до промпта interviewer`
- [x] **P7** живой запрос — см. ниже

## P7: живой запрос к модели (разрешение human:anthony 2026-10-17, «запускай»)

Скрипт — тот же клиент и параметры, что у живого хода: `PromptLibrary.interviewer_system()`
(7,296 символов), `OllamaClient`, `qwen2.5:14b-instruct`, temperature 0.75,
max_tokens 220, num_ctx 8192. Вопрос: «What is Anton working on now?», три сэмпла,
27 s вместе с загрузкой модели. После прогона `ollama stop`, `ollama ps` пуст.

> **1:** Anton is currently working on several projects for an SEO agency under NDA.
> These include a case-study platform, a donor search and outreach tool, and an email
> lead funnel. He's also selling AI automation services to Western SEO and
> link-building agencies and piloting YouTube Shorts automation for agencies.
>
> **2:** Anton is currently working on several projects. He's building a case-study
> platform, a donor search and outreach tool, and an email lead funnel for an SEO
> agency. He's also selling AI automation services to Western SEO and link-building
> agencies and piloting YouTube Shorts automation for agencies.
>
> **3:** Anton is currently working on several projects for an SEO agency under NDA,
> including a case-study platform, donor search and outreach, and an email lead
> funnel. He's also selling AI automation tools to Western SEO and link-building
> agencies and piloting YouTube Shorts automation for agencies.

| Что ждали | Сэмплов из 3 |
|---|---|
| работа для SEO-агентства | **3** |
| западные клиенты | **3** |
| «his own products» | **0** |
| звонки как канал продаж | **0** — модель пересказывает пункт без хвоста «then discovery calls in English» |

**Найдено живым прогоном:** строку «Piloting YouTube Shorts: automation for agencies
in 60 seconds» все три сэмпла прочли одинаково неверно — как «автоматизацию YouTube
Shorts для агентств», а это серия роликов, где он объясняет автоматизацию.
Двусмысленность текста, не ошибка модели: строка переписана («Piloting a YouTube
Shorts series where he explains automation for agencies in 60 seconds»). Живьём
правка НЕ перепроверена — это отдельный запуск модели; проверяется вместе с
сигналом наблюдения.
