// Thin REST client over fetch — one function per endpoint (doc 15).

import type {
  AddedWord,
  Debrief,
  InterviewDetail,
  InterviewListItem,
  ReviewDetail,
  TalkDetail,
  TalkListItem,
  UserSettings,
  VocabularyItem,
} from "../types/api";

export async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, init);
  if (!response.ok) {
    throw new Error(`${init?.method ?? "GET"} ${path} failed: ${response.status}`);
  }
  if (response.status === 204) return undefined as T;
  // Успешный ответ с HTML — это не «бэкенд сломался», а «до бэкенда не дошли»:
  // dev-сервер отдал страницу приложения, потому что префикс не проксируется.
  // Без этой проверки ошибка выглядела как `Unexpected token '<'`, и вкладки
  // History и Words молчали об истинной причине 38 дней (delivery diagnosis.md).
  const kind = response.headers.get("content-type") ?? "";
  if (!kind.includes("json")) {
    throw new Error(
      `${init?.method ?? "GET"} ${path}: ответ не JSON (${kind || "без content-type"}) — ` +
        `похоже, префикс не проксируется dev-сервером, проверь server.proxy в vite.config.ts`,
    );
  }
  return (await response.json()) as T;
}

// Отдельно от request<T>: `void` как аргумент generic'а запрещён
// (@typescript-eslint/no-invalid-void-type) и всё равно врал бы про тело ответа.
async function requestNoContent(path: string, init?: RequestInit): Promise<void> {
  const response = await fetch(path, init);
  if (!response.ok) {
    throw new Error(`${init?.method ?? "GET"} ${path} failed: ${response.status}`);
  }
}

export const api = {
  listInterviews: () =>
    request<{ items: InterviewListItem[] }>("/sessions/interviews").then((r) => r.items),
  getInterview: (id: string) => request<InterviewDetail>(`/sessions/interviews/${id}`),
  getReview: (id: string) => request<ReviewDetail>(`/sessions/reviews/${id}`),
  deleteInterview: (id: string) =>
    requestNoContent(`/sessions/interviews/${id}`, { method: "DELETE" }),
  minimalSummary: (id: string) =>
    request<{ debrief: Debrief }>(`/sessions/interviews/${id}/minimal-summary`, {
      method: "POST",
    }),
  listTalks: () => request<{ items: TalkListItem[] }>("/sessions/talks").then((r) => r.items),
  getTalk: (id: string) => request<TalkDetail>(`/sessions/talks/${id}`),
  addNoteToWords: (talkId: string, n: number) =>
    request<AddedWord>(`/sessions/talks/${talkId}/notes/${n}/vocabulary`, { method: "POST" }),
  // Адрес, а не запрос: WAV проигрывает сам браузер (`new Audio(url)`), темп — с сервера.
  noteAudioUrl: (talkId: string, n: number) => `/sessions/talks/${talkId}/notes/${n}/audio`,
  listVocabulary: (query: string) =>
    request<{ items: VocabularyItem[] }>(
      query ? `/vocabulary?q=${encodeURIComponent(query)}` : "/vocabulary",
    ).then((r) => r.items),
  deleteVocabulary: (id: string) => requestNoContent(`/vocabulary/${id}`, { method: "DELETE" }),
  getSettings: () => request<UserSettings>("/settings"),
  patchSettings: (patch: Partial<UserSettings>) =>
    request<UserSettings>("/settings", {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(patch),
    }),
};
