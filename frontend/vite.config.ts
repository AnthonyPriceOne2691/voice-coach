import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5273, // 5173 занят проектом линкбилдинга
    fs: {
      // ':' в пути репозитория (Other:Another) ломает сравнение путей в allow-list Vite
      strict: false,
    },
    proxy: {
      "/api": "http://127.0.0.1:8000",
      "/health": "http://127.0.0.1:8000",
      "/ws": { target: "ws://127.0.0.1:8000", ws: true },
    },
  },
});
