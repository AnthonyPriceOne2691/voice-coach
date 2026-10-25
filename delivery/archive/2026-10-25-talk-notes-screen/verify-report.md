# Verify report: talk-notes-screen (D3a.2 — 2 из 3, слой 2 из 2)

Дата прогонов: 2026-10-25. Builder: agent:claude-code (параллельная сессия, worktree
`.claude/worktrees/agent-a83fad904ac8715eb`). Verifier: human:anthony.

**CI run:** PR #52, коммит `6b6eb34` (весь код и тесты поставки, ветка слита с
`main` `1fa99e5`): `CI` https://github.com/AnthonyPriceOne2691/voice-coach/actions/runs/40224128816
— **success** (по логу: ruff «All checks passed!», mypy «no issues found in 62 source
files», «404 passed», coverage 96.47%); `quality`
https://github.com/AnthonyPriceOne2691/voice-coach/actions/runs/40224128788 — **success**
(по логу: pre-commit STRICT=1 — все хуки Passed, jscpd 0 клон-пар, complexity 0,
layers — 2 половины, ESLint warnings 1 при снимке 1; contour-doctor DEAD 0;
baseline-ratchet — 15 снимков; новых зависимостей нет; smoke S1–S6 ok; okf_sync_gate —
6 концептов, okf_validate — 0 ошибок; предупреждения шагов diff-coverage и mutation —
в «Что CI на этом PR не судит»). Первый прогон — на `4101a3e`, до теста секций
History: `CI` https://github.com/AnthonyPriceOne2691/voice-coach/actions/runs/40223372166
и `quality` https://github.com/AnthonyPriceOne2691/voice-coach/actions/runs/40223372135 —
оба **success**. Прогоны на итоговом коммите этого отчёта (только `delivery/`) — в PR.

## Оракулы спеки

| id | Оракул | Результат |
|---|---|---|
| C10 | `LanguageNotes.test.tsx`: «каждая заметка — you said → better», «без заметок — честное пустое состояние»; `TalkPage.test.tsx`: «после разговора — его заметки по session_id» | **PASS** — «You said: “…”» и «→ лучше — причина», без причины нет тире, ни одной оценки; пусто — без кнопок и похвалы; после конца разговора — `GET /sessions/talks/t9` |
| C11 | `LanguageNotes.test.tsx`: Listen (3 теста) | **PASS** — WAV по адресу своей заметки, `play` один раз; отказ звука виден; уход заметок с экрана — `pause` один раз |
| C12 | `LanguageNotes.test.tsx`: Add (4 случая) | **PASS** — `added` и `exists` гасят кнопку, запрос один и по адресу своей заметки; 502 — «Couldn't add — try again», кнопка жмётся снова; пока ответа нет — «Adding…», второй клик второго запроса не шлёт |
| C13 | `HistoryPage.test.tsx` (3 теста) | **PASS** — секция Talks: «· 12 min», «· not finished» у брошенного, «2 language notes» / «No language notes»; открытый разговор — заметки и транскрипт; назад — список; секции идут Interviews, затем Talks, у строки интервью та же голова («Interrupted», «not finished») |
| C10–C13 (REST) | поставка talk-notes-rest, `main` | в `main` (`a97a621`), проверено там |
| живое | Listen голосом Piper, снимок, Add на модели | **не прогонялось** — по «запускай» (`eval-smoke.md`) |

Тесты перенесённого `f0fe001` (здесь `3cb3efd`) на коде `main` без экрана — красные,
и по правильной причине: `LanguageNotes.test.tsx` не собирается («Failed to resolve
import "./LanguageNotes"»), `HistoryPage.test.tsx` — «Unable to find … 2 language
notes» и «… button "Open"», новый тест `TalkPage.test.tsx` — «Unable to find …
Language notes»; три прежних теста TalkPage зелёные. Фронт `main` — 57 тестов в 11
файлах, ветка — 70 в 13: десять перенесённых и три новых — уборка звука (C11), Add в
полёте (C12) и секции History со строкой интервью (C13).

## Перенос на main: чистый cherry-pick — ещё не перенос

Оба коммита легли на `origin/main` без единого конфликта, и типы сошлись с тем, что
отдаёт REST: `TalkListItem`/`TalkDetail` — с `routes_talks.py::_talk_item` и
`get_talk`, `AddedWord` — с `_outcome`, `LanguageNote` — с тем, что пишет
`orchestrator/tips.py::decide` и `talk_checks.py` (`turn_index` плюс `kind`, `said`,
`better`, `why`, `spoken`). Расхождений, которые пришлось бы чинить, нет.

Первый же прогон фронта на `main` дал **2 failed | 65 passed (67)**: оба теста Listen.
Экран собирали на vitest 2 (`59231ed`: `"vitest": "^2.1.8"`), а deps-refresh поднял
`main` до 5 (`^5.0.5`, `8d344d4`). С vitest 4 `vi.fn(() => ({ play }))` под `new` не
вызывается: `new Audio(url)` в обработчике клика бросал `TypeError … is not a
constructor`, и до `play()` дело не доходило. Красный при этом называл чужую причину
— «expected "vi.fn()" to be called 1 times, but got 0 times» и «Unable to find … Can't
play right now»: без чтения лога его легко «починить» в компоненте. Двойник стал
классом (`4814039`), как `AudioContext` и `WebSocket` в `useVoiceSession.test.tsx`;
код экрана не менялся. Урок L111.

## Находка ревью: Listen играл мимо эхо-защиты

Listen проигрывает фразу через `new Audio(url)` — мимо очереди сессии, и колбэк
«отзвучало» из `AudioQueue`, по которому `useVoiceSession` открывает запись, о ней не
знает. Фраза до 20 слов (`MAX_FRAGMENT_WORDS`), начатая перед «Start talking», могла
доиграть в уже открытый микрофон — VAD принял бы голос Генри за реплику Антона. Ни
один тест экрана этого не видел: jsdom звука не играет и микрофона не открывает.

Починка (`b0258ff`): у списка один набор начатых звуков (`usePlayer`), уборка при
уходе с экрана глушит каждый. Заметки уходят с экрана раньше, чем откроется запись:
`start` сбрасывает `ended` в самом начале, до `getSettings` и `openMicrophone`, а
смена вкладки снимает страницу целиком. Сторож — «заметки ушли с экрана — фраза
смолкла» (C11), мутация MF13 убита. Правило записано в концепт эхо-защиты, и
`LanguageNotes.tsx` вошёл в его `implementation:` — правка компонента теперь пройдёт
мимо OKF-гейта, только если концепт сверен. Урок L112.

## Мутации (сторож обязан краснеть, L62)

Скрипт мутаций — во временном каталоге сессии (в репозиторий не едет): точная замена
одной строки, прогон своих тест-файлов, откат `git checkout`; до старта база зелёная
(`Tests 16 passed (16)` по трём файлам). Мутационный шаг CI фронт не судит: он считает
python-половину, а Stryker во `frontend/` не установлен (см. «Машинные гейты»), —
вердикт по фронту даёт только этот прогон.

| Мутация | Пример | Результат |
|---|---|---|
| MF1: причина выводится всегда — пустая даёт висячее тире | C10 | **убита** — 1 failed \| 8 passed (9) |
| MF2: «You said» показывает лучший вариант, а не сказанное | C10 | **убита** — 1 failed \| 8 passed (9) |
| MF3: Listen играет первую заметку, а не свою | C11 | **убита** — 1 failed \| 8 passed (9) |
| MF4: отказ звука проглочен молча | C11 | **убита** — 1 failed \| 8 passed (9) |
| MF5: после «добавлено» кнопка снова жмётся | C12 | **убита** — 2 failed \| 7 passed (9) |
| MF6: после ошибки повторить нельзя | C12 | **убита** — 1 failed \| 8 passed (9) |
| MF7: Add шлёт запрос не по адресу заметки | C12 | **убита** — 1 failed \| 8 passed (9) |
| MF8: History не показывает разговоров | C13 | **убита** — 3 failed (3) |
| MF9: брошенный разговор показан с длительностью (L16) | C13 | **убита** — 2 failed \| 1 passed (3) |
| MF10: открытый разговор без транскрипта | C13 | **убита** — 1 failed \| 2 passed (3) |
| MF11: строка разговора без числа заметок | C13 | **убита** — 3 failed (3) |
| MF12: после разговора заметки не запрошены | C10 | **убита** — 1 failed \| 3 passed (4) |
| MF13: уход заметок с экрана не глушит Listen | C11 | **убита** — 1 failed \| 8 passed (9) |
| MF14: пока Add в полёте, кнопка жмётся — второй запрос | C12 | **убита** — 1 failed \| 8 passed (9) |
| MF15: секция интервью снова «Recent sessions» | C13 | **убита** — 1 failed \| 2 passed (3) |
| MF16: голова строки не различает закрытую и прерванную сессию | C13 | **убита** — 1 failed \| 2 passed (3) |

Итог: 16 мутаций, выжило 0. Не сторожится: форма единственного числа «1 language
note» (в тестах 2 и 0) — косметика, мутацией не проверялась.

**Находка мутаций:** сторожа на миг полёта Add не было. talk-notes-rest закрыла гонку
двух Add на одну заметку экраном («кнопка Adding… не жмётся»), а перенесённые тесты
проверяли только исходы `added`, `exists` и 502 — MF5 и MF6 бьют по ним, состояние
`busy` не трогал никто. Добавлен тест «пока идёт запрос — Adding…» (`a205177`),
MF14 убита.

**Находка первого CI:** строка интервью в History не исполнялась ни одним тестом.
Шаг diff-coverage напомнил, что покрытие фронта не измеряется (ниже), а перенос
головы строки интервью в `SessionWhen` в заглушке бэкенда без интервью не рендерился
вовсе. Добавлен тест «две секции — Interviews, под ней Talks» с брошенным интервью
(`6b6eb34`), MF15 и MF16 убиты.

## Машинные гейты

После слияния `origin/main` (`1fa99e5`, memory-guard):

| Гейт | Результат |
|---|---|
| `UV_FROZEN=1 ./scripts/run_checks.sh` | **PASS** — бэкенд не тронут: 404 passed, coverage 96.47% (гейт 85), mypy strict, ruff, модули ≤ 500 строк |
| `STRICT=1 pre-commit run --all-files` | **PASS** — все хуки; jscpd 0 клон-пар (python + ts, снимок 0), сложность 0 (python + ts), слои OK (import-linter + dependency-cruiser), ESLint warnings 1 при снимке 1 |
| `npx vitest run` | **PASS** — 70 тестов в 13 файлах |
| `npm run build` (`artifact_oracle`) | **PASS** — `tsc -b` + `vite build`; в собранном CSS слой заметок есть: `grep -c note-better dist/assets/*.css` → 1 (L46: потерянный `@import` сборку не роняет) |
| `bash delivery/evals/smoke/run.sh` | **PASS** — S1–S6 ok, S7 (health) пропущен: сервер не поднят |
| `okf_sync_gate.py --base origin/main`, `okf_validate.py` | **PASS** — 5 mapped concepts, 0 warnings; 0 errors, 13 files |
| `delivery_check.py --diff-base origin/main` | 0 ошибок; предохранитель — 14 файлов, net +712 (+742/−30) при лимите 800 |

Поверхность модели (`model_surface`) не задета: дифф — фронт, docs 11 и 17, концепт
эхо-защиты.

### Покрытие фронта не измеряется — что не исполнено тестами

CI-шаг diff-coverage на этом PR: «Python-файлов в диффе нет, но изменено 9
prod-файл(ов). Покрытие этих файлов не измерено». Провайдера покрытия у vitest во
`frontend/` нет (`@vitest/coverage-v8` не установлен; новая зависимость — решение
человека), поэтому непокрытое названо чтением кода против тестов:

- `LanguageNotes.tsx` — ветка отказа `EndedTalkNotes` («Failed to load language
  notes — is the backend running?»); «Loading…» рендерится в тесте TalkPage, но не
  утверждается; уборка с двумя начатыми звуками (тест — с одним).
- `TalkHistory.tsx` — `notesLabel(1)` («1 language note»); отказы `listTalks` и
  `getTalk` в `TalkList`; пустое состояние «No talks yet — start one on the Talk tab.»
- `HistoryPage.tsx` — у строки интервью исполнена только таблетка «Not reviewed»;
  «Reviewed», «Full summary», «Minimal summary», деталь интервью, разбор и удаление —
  прежнее поведение, тестов на фронте у него не было и до поставки.
- `styles.css`, `styles/notes.css`, `types/api.ts` — исполняемого кода нет; вид —
  снимком по «запускай».

Непокрытое — тексты и ветки отказов. Логика, на которой держатся C10–C13, тестами
исполнена, и её мутанты MF1–MF16 убиты.

### Что CI на этом PR не судит (по логу `quality`)

- **Мутации фронта.** Шаг «Mutation testing (changed files, budgeted)»: «TS-половина
  (frontend/src) этим прогоном НЕ судится — считается python» и «изменённых
  prod-файлов нет (BASE=origin/main, смотрел в backend/app)». Stryker во `frontend/`
  не установлен (известно с mutation-gate); вердикт по фронту — MF1–MF16 выше.
- **Архивированную поставку.** Поставка ушла в архив в том же PR, `delivery/active/`
  пуст, и шаг «Delivery phase gate» идёт веткой без `--diff-base`: «idle: нет
  delivery/active/STATUS.md», 0 ошибок. Архив `2026-10-25-talk-notes-screen`
  (phase=handoff) судили pre-push (`delivery-gate` с базой `origin/main`) и ручной
  прогон: 0 ошибок, 3 предупреждения — разобраны ниже.
- **Аудит зависимостей** печатает «не найдено ни одного поддерживаемого манифеста»:
  проверка только в корне (L95), зависимости поставка не меняет.

### Оставшиеся предупреждения

- **§3.1d: «примеры появились в истории ПОЗЖЕ ссылающихся на них тестов: C10, C11,
  C12, C13».** Ложная тревога переноса. Примеры C10–C13 есть в истории с 2026-10-17
  (`d9a7f9d`, правка спеки человеком) и в спеке talk-notes с 2026-10-23 19:25
  (`29156f9`); тесты написаны после подписи — `f0fe001`, 2026-10-23 19:46. Проверка
  смотрит окно этой ветки и `delivery/active/spec.md`, а выжимка спеки легла
  коммитом после cherry-pick'ов. Порядок коммитов ради гейта не переставлялся.
- **Реляционный оракул (§6.5)** — решение человека 2026-08-12: зависимость для
  тестов-свойств не добавляется.

## Находка верификации: §6.5a в этом репозитории не судит вовсе

`artifact_oracle` объявляли 11 архивных поставок (`cd frontend && npm run build`), и
ни одно объявление гейт не прочёл. Замер на `delivery_artifact.py`:

- `declares_build(ROOT)` → `''`: признак сборки ищется только в корневом
  `package.json`, а фронт — в `frontend/` (`declares_build(ROOT/'frontend')` →
  `'package.json'`);
- STATUS класса M на `handoff` **без строки** `artifact_oracle` — 0 ошибок,
  0 предупреждений;
- будь корень `frontend/`, принятая здесь форма объявления не прошла бы:
  «artifact_oracle: cd — файла нет» — гейт ждёт путь к файлу проверки, а не команду.

Остальные гейты контура знают про подкаталог (`LINT_FE_DIR`), этот — нет. Механика
контура (`scripts/delivery_*`) здесь не правится: место — полевой отчёт в канон.
Сама сборка — проверка компиляции, а не инвариант артефакта; дешёвую проверку
собранного (`.note-better` в CSS) я сделал руками, и она записана выше. Урок L113.

## Ревью рисковых мест (§12.5)

Маячок поднят классом «новый модуль»: `LanguageNotes.tsx`, `TalkHistory.tsx`,
`SessionWhen.tsx` и тесты к ним. Других классов дифф не задел — ни транзакций, ни
сети, ни денег: всё через существующий `api` (`fetch`).

1. **новый модуль `LanguageNotes.tsx`** — состояние: набор начатых звуков в
   `usePlayer` и у каждой заметки свои `add` и `silent` в `NoteRow`. Что реально
   может сломаться: (а) уборка гасит звук, чей `play()` ещё не начался, — его промис
   отклоняется (`AbortError`), и `NoteRow` зовёт `setSilent(true)` уже после
   размонтирования; React 18 это молча пропускает, на экране ничего не видно. (б) В
   StrictMode эффект монтируется дважды — первая уборка гасит пустой набор, вреда
   нет. (в) Набор растёт с каждым нажатием Listen за время монтирования — граница —
   число нажатий, у списка из нескольких заметок это единицы. (г) `EndedTalkNotes`
   не отменяет запрос при смене `talkId`, но между разговорами компонент
   размонтируется (`start` сбрасывает `ended`), так что опоздавший ответ попадает в
   снятый компонент, а не в чужой список.
2. **новый модуль `TalkHistory.tsx`** — `TalkList` берёт одну страницу
   `api.listTalks()` (по умолчанию сервера — 50 разговоров), как и Interviews
   (`listInterviews`); пятьдесят первый разговор в History не виден. Риск назван и
   не закрыт — так же, как у интервью, страницы в интерфейсе нет. `open` в
   `TalkList` не защищён от двойного клика: два `getTalk` и два `onOpen` с одной
   деталью — безвредно. `TalkDetailPanel` отдаёт `talk.language_notes` в
   `LanguageNotes` как есть — фильтровать заметки экран не вправе (инвариант 1).
3. **новый модуль `SessionWhen.tsx`** — голова строки у интервью и разговора одна;
   тип `Span` берёт поля из `TalkListItem`, а `InterviewListItem` подходит
   структурно. Переименование поля в одном из списков ловит `tsc -b`, а «not
   finished» живёт в одном месте — в `formatSessionSpan` (L16).
4. **граница с REST** — `addNoteToWords` и `noteAudioUrl` строят адрес по индексу
   заметки в `language_notes`, ровно как `routes_talks.py::_note`; гонку двух Add на
   одну заметку (talk-notes-rest, §12.5 п.1) экран не создаёт: пока идёт запрос,
   кнопка — `Adding…` и не жмётся (тест полёта, MF14). Остаётся гонка из двух мест
   сразу — та же заметка открыта после разговора на Talk и в History другой
   вкладкой браузера; человек один, риск назван и не закрыт.

## Исполнение рисковых путей (§12.6)

- `frontend/src/components/LanguageNotes.tsx` — исполнил
  `npx vitest run src/components/LanguageNotes.test.tsx` (jsdom, двойник `Audio`):
  `new Audio("/sessions/talks/t1/notes/1/audio")`, `play` один раз; отклонённый
  `play()` — «Can't play right now»; размонтирование — `pause` один раз; и
  `npm run build` — компонент и `.note-better` в собранном бандле. **Не исполнено:**
  звук в настоящем браузере (WAV голосом Piper через прокси `/sessions`, политика
  автозапуска на клике) и вид экрана — браузерный стенд и живой стек этой сессии
  запрещены. Отложено по «запускай» human:anthony: `eval-smoke.md`, раздел «Живое», и
  сигнал наблюдения. at=2026-10-25

## Решения для человека

Новых нет. Три решения 2026-10-23 (возврат удалённого слова, секции Interviews и
Talks, категория `fluency`) исполнены: первое и третье — на сервере (talk-notes-rest),
второе — здесь. Решения агента — `decisions.md`.

## Уроки

- **L111:** чистый cherry-pick — ещё не перенос. Коммиты экрана легли на `main` без
  единого конфликта, а два теста Listen покраснели: deps-refresh поднял vitest 2 → 5,
  и `vi.fn` со стрелкой больше не конструируется под `new`. Красный называл чужую
  причину («play вызван 0 раз», «не найден текст отказа»), то есть звал чинить
  компонент. Собранное на старом тулчейне гоняется на тулчейне цели до любых выводов;
  двойник конструктора — класс.
- **L112:** эхо-защита видит только свою очередь. Микрофон открывается по колбэку
  «отзвучало» `AudioQueue`, а звук, сыгранный мимо неё (`new Audio(url)` у Listen),
  для неё не существует: фраза до 20 слов могла доиграть в открытый микрофон новой
  сессии. jsdom звука не играет и микрофона не открывает, поэтому сьют был зелёным.
  Любой путь проигрывания вне сессии обязан гаснуть раньше, чем откроется запись, —
  правило в концепте, путь в `implementation:`.
- **L113:** §6.5a в этом репозитории молчит с развёртывания: `declares_build` ищет
  сборку только в корневом `package.json`, фронт — в `frontend/`, и STATUS без
  `artifact_oracle` проходит handoff без единого слова. 11 объявлений
  `cd frontend && npm run build` никем не судились, а гейт, смотри он в подкаталог,
  отверг бы их («cd — файла нет»). Тот же класс, что L3: гейт без половины снаружи
  неотличим от зелёного.

## Verdict

**READY FOR HANDOFF** — экранная половина C10–C13 зелёная на тулчейне `main`, 16
мутаций сторожей убиты, машинные гейты и CI (`CI`, `quality`) зелёные по правилам
delivery@2.07 · cqg@2.74. Найдено и закрыто по пути: двойник `Audio` под vitest 5,
звук Listen мимо эхо-защиты, несторожёный миг полёта Add и неисполненная строка
интервью в History. Открыто — живое по «запускай»: Listen голосом Piper в браузере,
снимок экрана, Add на настоящей модели.

## Assertion digest (ревью ожиданий, не кода)

База: `origin/main` · сгенерировано `assert_digest.sh`

Новых/изменённых утверждений: **35**, из них без ссылки на пример спеки:
**0**. Вопрос к каждому непривязанному один: **откуда взято ожидаемое
значение — из спеки или придумано под реализацию?**

```
C10	expect(first.textContent).toContain("You said: “I go to the office and meet my client”"); // C10
C10	expect(first.textContent).toContain("→ I went to the office and met my client — past tense"); // C10
C10	expect(second.textContent).toContain("→ the food was delicious"); // C10
C10	expect(second.textContent).not.toContain(" — "); // C10: причины нет — нет и тире
C10	expect(document.body.textContent).not.toMatch(/score|grade|rating|level|\d\s*\/\s*10/i); // C10
C10	expect(screen.getByText(/No language notes for this talk/)).toBeTruthy(); // C10
C10	expect(screen.queryByRole("button")).toBeNull();
C10	expect(document.body.textContent).not.toMatch(/great|perfect|excellent/i); // C10
C11	expect(audio).toHaveBeenCalledWith("/sessions/talks/t1/notes/1/audio"); // C11
C11	expect(play).toHaveBeenCalledTimes(1); // C11
C11	expect(await screen.findByText("Can't play right now")).toBeTruthy(); // C11
C11	expect(pause).not.toHaveBeenCalled(); // C11: пока заметки на экране — звучит
C11	expect(pause).toHaveBeenCalledTimes(1); // C11: эхо-защита
C12	expect(done).toHaveProperty("disabled", true); // C12: повтор с экрана не уходит
C12	expect(calls).toEqual(["POST /sessions/talks/t1/notes/1/vocabulary"]); // C12
C12	expect(await screen.findByRole("button", { name: label })).toHaveProperty("disabled", disabled); // C12
C12	expect(busy).toHaveProperty("disabled", true); // C12
C12	expect(calls).toEqual(["POST /sessions/talks/t1/notes/0/vocabulary"]); // C12: двух Add нет
C13	expect(await screen.findByText("2 language notes")).toBeTruthy(); // C13
C13	expect(screen.getByText("No language notes")).toBeTruthy(); // C13
C13	expect(spans.some((span) => span?.endsWith("· 12 min"))).toBe(true); // C13: длительность
C13	expect(spans.some((span) => span?.endsWith("· not finished"))).toBe(true); // C13 (L16)
C13	expect(await screen.findByText("Language notes")).toBeTruthy(); // C13
C13	expect(screen.getByRole("listitem").textContent).toContain("→ I went to the office"); // C13
C13	expect(screen.getByText("Yesterday I go to the office.")).toBeTruthy(); // C13: транскрипт
C13	expect(asked).toContain("/sessions/talks/t1");
C13	expect(await screen.findByText("2 language notes")).toBeTruthy();
C13	expect(await screen.findByText("Not reviewed")).toBeTruthy(); // C13: строка интервью
C13	expect(await screen.findByText("2 language notes")).toBeTruthy(); // C13
C13	expect(titles).toEqual(["Interviews", "Talks"]); // C13: решение human:anthony 2026-10-23
C13	expect(screen.getByText("Interrupted")).toBeTruthy(); // C13: голова — SessionWhen
C13	expect(screen.getAllByText(/· not finished$/)).toHaveLength(2); // C13: интервью и разговор
C10	expect(await screen.findByText("Language notes")).toBeTruthy(); // C10
C10	expect(screen.getByRole("listitem").textContent).toContain("→ Pretty good, thanks"); // C10
C10	expect(asked).toContain("/sessions/talks/t9"); // C10
```

✅ **Каждое утверждение ведёт к примеру спеки** (C10 C11 C12 C13), а примеры человек
подписал до кода (`human_ok_spec`). Подпись под дайджестом здесь
**не требуется**: она уже стоит, заранее и на числах. Пиши в verify-report
`asserts_reviewed_by: n/a (все утверждения ведут к одобренным примерам)`.

asserts_without_example: 0

asserts_reviewed_by: n/a (все утверждения ведут к одобренным примерам)

## Harness metrics (this shipment)

<!-- generated by scripts/delivery_metrics.py --base origin/main -->

| Metric | Value |
|---|---|
| files_touched / loc_diff | 14 code (+10 process docs) / +742/-30 (net +712) |
| commits | 13 на `6b6eb34`; коммит этого отчёта — четырнадцатый |
| time_to_accepted_spec | 0.0h |
| rework_after_done | 1 — счётчик видит 3 коммита после первого `phase: handoff` (`a13506f`): архив (`3a63658`), ссылка плана на свои уроки (`4101a3e`) и тест секций History (`6b6eb34`) по предупреждению diff-coverage первого CI — переделкой считаю только последний; код экрана после handoff не менялся |
| harness_hardened | yes — frontend/src/components/LanguageNotes.test.tsx (новый оракул), frontend/src/pages/HistoryPage.test.tsx (новый оракул) |
| implement_retries | 1 — перенос: два теста Listen покраснели на vitest 5 (двойник `Audio` стрелкой), починен двойник; правки по ревью (звук мимо эхо-защиты), по мутациям (миг полёта Add) и по предупреждению diff-coverage первого CI (строка интервью) — converge, а не повтор задачи |
| verify_fails_before_green | 0 — локальные гейты зелёные с первого полного прогона после починки двойника; CI зелёный на обоих прогонах (`4101a3e`, `6b6eb34`) — ссылки в шапке |
| est_token_or_cost | n/a |

MANUAL-поля заполняет агент/человек на handoff. Если `verify_fails_before_green >= 2` при `harness_hardened: no` — по §9.2 добавь oracle/breaker/hook в этой же поставке.
