// Разбор двух файлов, которые обязаны совпадать: путей клиента и правил
// dev-прокси. Вынесено из теста, чтобы не читать исходники регуляркой в
// нескольких местах и чтобы у самой сверки были тесты.
//
// Сверяются ПРЕФИКСЫ (первый сегмент пути), а не полные адреса: правил в
// прокси единицы, они меняются редко, и именно на уровне префикса произошёл
// разрыв 2026-07-05.

/** Первые сегменты путей, которые клиент запрашивает у бэкенда. */
export function apiPrefixes(source: string): string[] {
  // Пути в api.ts записаны литералом или шаблоном: "/sessions/interviews",
  // `/vocabulary/${id}`. Берём то, что стоит сразу после кавычки.
  const found = source.matchAll(/["'`](\/[a-z][a-z0-9-]*)(?=[/"'`?])/gi);
  return [...new Set([...found].map((m) => m[1]))].sort();
}

/** Ключи-префиксы из блока `server.proxy` в vite.config.ts. */
export function proxiedPrefixes(source: string): string[] {
  const block = /proxy\s*:\s*\{([\s\S]*?)\n\s*\},/.exec(source);
  if (!block) return [];
  const found = block[1].matchAll(/["'`](\/[a-z][a-z0-9-]*)["'`]\s*:/gi);
  return [...new Set([...found].map((m) => m[1]))].sort();
}
