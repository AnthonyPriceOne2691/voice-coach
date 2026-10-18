/**
 * dependency-cruiser: направление зависимостей между слоями (TS-половина роли).
 * Запуск — только через scripts/lint/check_layers_gate.sh: голый depcruise на
 * пустой области выходит НУЛЁМ («0 modules cruised»), и это зелёное на
 * непроверенном. Замер и таблица сравнения с import-linter — CQG §3.6.
 *
 * АДАПТАЦИЯ ПРОЕКТА (объявлена в scripts/lint/adapted.json). Шаблон канона
 * написан под фронт в корне репозитория (`^src/...`, `tsconfig.json` рядом).
 * Здесь фронт живёт в `frontend/`, а гейт зовёт depcruise ИЗ КОРНЯ — значит и
 * пути правил, и путь к tsconfig считаются от корня. С шаблонными путями
 * инструмент выходил ошибкой «Cannot read file 'tsconfig.json'», то есть
 * половина не судила вовсе.
 *
 * Слои этого фронта (сверху вниз):
 *   pages → components → hooks → lib → types
 * `types/` — только описания контракта с бэком, `lib/` — чистые функции и
 * клиенты. Оба обязаны оставаться листьями: их тянут все, и импорт вверх
 * замкнул бы граф.
 *
 * Легаси замораживается не отдельным снимком, а прямо в правиле — `pathNot`,
 * с пометкой TODO и тикетом. Тот же тающий baseline, только в контракте.
 */
const SRC = "^frontend/src";

module.exports = {
  forbidden: [
    {
      name: "types-is-leaf",
      comment: "types/ — контракт с бэком, он не знает про UI и логику (§2.3)",
      severity: "error",
      from: { path: `${SRC}/types` },
      to: { path: `${SRC}/(pages|components|hooks|lib)` },
    },
    {
      name: "lib-is-leaf",
      comment: "lib/ — чистые функции и клиенты; про React-слой они не знают (§2.3)",
      severity: "error",
      from: { path: `${SRC}/lib` },
      to: { path: `${SRC}/(pages|components|hooks)` },
    },
    {
      name: "hooks-no-ui",
      comment: "хук не импортирует страницы и компоненты — иначе слой развёрнут импортом обратно",
      severity: "error",
      from: { path: `${SRC}/hooks` },
      to: { path: `${SRC}/(pages|components)` },
    },
    {
      name: "components-no-pages",
      comment: "компонент не знает про страницу, которая его показывает",
      severity: "error",
      from: { path: `${SRC}/components` },
      to: { path: `${SRC}/pages` },
    },
    {
      name: "no-circular",
      comment: "цикл между модулями — направление потеряно",
      severity: "error",
      from: {},
      to: { circular: true },
    },
  ],
  options: {
    doNotFollow: { path: "node_modules" },
    // ⚠ Отдельный tsconfig, а не `frontend/tsconfig.json`, и это не дубль.
    // depcruise зовётся из КОРНЯ, а `include` тогда разрешается тоже от корня:
    // `include: ["src"]` фронтового конфига превращается в несуществующий
    // `<repo>/src`, и TS отвечает TS18003 «No inputs were found». Корневой
    // `tsconfig.depcruise.json` НАСЛЕДУЕТ фронтовый (компиляторные опции — одни
    // и те же, разъехаться нечему) и только пере-базирует `include`.
    //
    // `tsPreCompilationDeps` обязателен: без него не видно `import type`, а
    // контракт «types/ — лист» держится ровно на них. Замер: 36 зависимостей
    // без флага против 44 с ним — восемь связей типа были невидимы.
    // Резолвер канона (`cqg@2.16`): `LINT_TSCONFIG` перекрывает, иначе первый
    // существующий — здесь это `tsconfig.depcruise.json` в корне (порт 18.10).
    tsConfig: {
      fileName:
        process.env.LINT_TSCONFIG ||
        [
          "tsconfig.depcruise.json",
          `${process.env.LINT_FE_DIR || "frontend"}/tsconfig.json`,
          "tsconfig.json",
        ].find((p) => require("fs").existsSync(p)) ||
        "tsconfig.json",
    },
    tsPreCompilationDeps: true,
    exclude: { path: "(\\.test\\.|\\.spec\\.|__tests__)" },
  },
};
