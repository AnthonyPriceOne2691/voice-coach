// Thin REST client over fetch — one function per endpoint (doc 15).

import type { Debrief, InterviewDetail, InterviewListItem, ReviewDetail, VocabularyItem } from "../types/api";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, init);
  if (!response.ok) {
    throw new Error(`${init?.method ?? "GET"} ${path} failed: ${response.status}`);
  }
  return response.status === 204 ? (undefined as T) : ((await response.json()) as T);
}

export const api = {
  listInterviews: () =>
    request<{ items: InterviewListItem[] }>("/sessions/interviews").then((r) => r.items),
  getInterview: (id: string) => request<InterviewDetail>(`/sessions/interviews/${id}`),
  getReview: (id: string) => request<ReviewDetail>(`/sessions/reviews/${id}`),
  deleteInterview: (id: string) =>
    request<void>(`/sessions/interviews/${id}`, { method: "DELETE" }),
  minimalSummary: (id: string) =>
    request<{ debrief: Debrief }>(`/sessions/interviews/${id}/minimal-summary`, {
      method: "POST",
    }),
  listVocabulary: (query: string) =>
    request<{ items: VocabularyItem[] }>(
      query ? `/vocabulary?q=${encodeURIComponent(query)}` : "/vocabulary",
    ).then((r) => r.items),
  deleteVocabulary: (id: string) => request<void>(`/vocabulary/${id}`, { method: "DELETE" }),
};
