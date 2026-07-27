// Thin REST client over fetch — one function per endpoint (doc 15).

import type {
  Debrief,
  InterviewDetail,
  InterviewListItem,
  ReviewDetail,
  VocabularyItem,
} from "../types/api";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, init);
  if (!response.ok) {
    throw new Error(`${init?.method ?? "GET"} ${path} failed: ${response.status}`);
  }
  return response.status === 204 ? (undefined as T) : ((await response.json()) as T);
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
  listVocabulary: (query: string) =>
    request<{ items: VocabularyItem[] }>(
      query ? `/vocabulary?q=${encodeURIComponent(query)}` : "/vocabulary",
    ).then((r) => r.items),
  deleteVocabulary: (id: string) => requestNoContent(`/vocabulary/${id}`, { method: "DELETE" }),
};
