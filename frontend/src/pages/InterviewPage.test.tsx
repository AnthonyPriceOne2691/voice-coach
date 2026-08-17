// @vitest-environment jsdom
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { InterviewPage } from "./InterviewPage";

/**
 * Сторож на КРЮЧОК, а не на вид.
 *
 * Браузерный стенд (`delivery/evals/browser/stand.py`) начинает прогон с клика по
 * кнопке старта и до 2026-08-17 искал её по ПОДПИСИ («Start Mock Interview»).
 * Переработка интерфейса переименовала кнопку в «Start interview» — стенд четыре
 * дня отчитывался `mic-never-opened`, то есть врал не только про результат, но и
 * про предмет: микрофон был не при чём.
 *
 * Тест сторожит атрибут, от которого стенд теперь зависит. Подпись менять можно —
 * крючок нельзя, и об этом скажет красный тест, а не молчание стенда.
 */
afterEach(cleanup);

describe("InterviewPage", () => {
  it("кнопка старта несёт крючок для браузерного стенда", () => {
    render(<InterviewPage reviewTarget={null} onReviewStarted={vi.fn()} />);

    const start = screen.getByTestId("start-interview"); // R2
    expect(start.tagName).toBe("BUTTON");
    // Подпись проверяется отдельно и мягко: она может меняться, крючок — нет.
    expect(start.textContent?.toLowerCase()).toContain("start");
  });
});
