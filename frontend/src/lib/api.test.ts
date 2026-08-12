import { describe, expect, it } from "vitest";
// Исходники читаются через `?raw` — возможность самого сборщика. Node-овский
// fs потребовал бы @types/node ради одного теста, то есть новой зависимости
// на годы; `vite/client` уже в tsconfig.types.
import apiSource from "./api.ts?raw";
import viteConfigSource from "../../vite.config.ts?raw";
import { apiPrefixes, proxiedPrefixes } from "./devProxy";

describe("dev-proxy покрывает все префиксы api.ts (C5)", () => {
  // Сторож, а не украшение. 2026-07-05 в api.ts появились /sessions и
  // /vocabulary, в vite.config.ts их не добавили, и вкладки History и Words
  // не работали 38 дней: сборка зелёная, юнит-тесты зелёные, запрос уходит в
  // SPA-fallback и возвращает HTML с кодом 200. Забытый префикс обязан ронять
  // тест, а не вкладку в браузере.
  it("каждый префикс клиента есть в прокси", () => {
    const client = apiPrefixes(apiSource);
    const proxied = proxiedPrefixes(viteConfigSource);
    expect(client.length).toBeGreaterThan(0); // C5 — регулярка не разучилась читать пути
    expect(client.filter((p) => !proxied.includes(p))).toEqual([]); // C5
  });

  it("сторож не всегда-зелёный: выдуманный префикс он замечает", () => {
    const client = apiPrefixes(`request<T>("/reports/weekly")`);
    const proxied = proxiedPrefixes(viteConfigSource);
    expect(client).toEqual(["/reports"]); // C5
    expect(client.filter((p) => !proxied.includes(p))).toEqual(["/reports"]); // C5
  });
});

describe("ошибка отличает «не JSON» от «бэкенд молчит» (C4)", () => {
  it("HTML вместо JSON называет причину", async () => {
    const { request } = await import("./api");
    const html = new Response("<!doctype html><html></html>", {
      status: 200,
      headers: { "content-type": "text/html" },
    });
    globalThis.fetch = () => Promise.resolve(html);
    await expect(request("/sessions/interviews")).rejects.toThrow(/не JSON.*прокси/i); // C4
  });

  it("настоящая ошибка бэкенда остаётся собой", async () => {
    const { request } = await import("./api");
    globalThis.fetch = () => Promise.resolve(new Response("nope", { status: 500 }));
    await expect(request("/sessions/interviews")).rejects.toThrow(/500/); // C4
  });
});
