import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  // Плагин нужен ТЕСТАМ, а не только сборке: без него JSX в `*.test.tsx`
  // не трансформируется.
  plugins: [react()],
  test: {
    // `node` остаётся умолчанием: логические тесты (`lib/**`) в DOM не нуждаются,
    // а jsdom стоит времени старта. Компонентные включают его сами строкой
    // `// @vitest-environment jsdom` — заведено 2026-08-13 вместе с экраном
    // Settings, где впервые понадобилось проверить ПОВЕДЕНИЕ разметки.
    environment: "node",
    include: ["src/**/*.test.ts", "src/**/*.test.tsx"],
  },
});
