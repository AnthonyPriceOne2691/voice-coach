# Eval smoke — this shipment

Derived from spec acceptance (G1–G6).

## Оракулы поставки

- [x] **G1** подсказка проходит: «You should open with the metric…»,
      «Try saying it in one sentence first.»
- [x] **G2** похвала проходит: «Great answer — you led with the trade-off.»
- [x] **G3** баллы режутся: «I'd score that a four.»
- [x] **G4** итоговый разбор режется: «Overall your performance today was solid.»
- [x] **G5** нетронутые инварианты держатся: русский и четвёртое предложение
      по-прежнему режутся
- [x] **G6** живая модель с новым промптом помогает, а не давит

## Как выглядела красная сторона

На СТАРОМ контракте новый тест давал **4 провала из 6**: три подсказки резались
(`You should…`, `Great answer…`, `Try saying…`), а итоговый разбор проходил —
в списке запрещённых его не было вовсе.

⚠ **Первая версия теста была бесполезной, и это стоит записать.** Фразы были
подобраны так, что случайно обходили запрещённые паттерны («Try opening…»
вместо «Try saying…»), и тест зеленел ДО правки. Такой сторож не сторожит
ничего — урок L12 в чистом виде. Формулировки заменены на те, что контракт
реально резал.

## G6 дословно

```
>>> Honestly I'm not sure how to answer that. I don't know where to start.
<<< That's okay. Let's start with the problem it solved and work from there.
    Can you describe a specific challenge your team faced?

>>> Sorry, I don't understand what you mean.
<<< No problem! Let's talk about the LinkBuilder SaaS. Can you describe its architecture?
```

Второй ответ опирается на знание портфолио из поставки
`2026-08-12-portfolio-knowledge` — два изменения сложились.

## Продуктовые оракулы

- [x] сьют **104 теста** (было 98), покрытие 93.01%
- [x] `pre-commit run --all-files` — 0 провалов
- [x] `delivery/evals/smoke/run.sh`

## Чего эта поставка НЕ делает

Реакция на «говори медленнее» (поставка 2), soft skills (3), выразительная
речь с паузами (4). Генри стал добрым, но темпом речи по просьбе он пока не
управляет.
