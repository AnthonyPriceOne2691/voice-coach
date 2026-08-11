import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import "./styles.css";

// Явная проверка вместо `!`: non-null assertion гасит единственный сигнал о том,
// что index.html разошёлся с точкой монтирования. Пустой экран без единого
// сообщения — самый дорогой сорт отказа фронта.
const root = document.getElementById("root");
if (!root) throw new Error("#root not found in index.html — точка монтирования потеряна");

createRoot(root).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
