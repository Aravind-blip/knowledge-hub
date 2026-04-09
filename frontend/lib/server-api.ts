import { cache } from "react";

import type { DocumentListResponse, SessionResponse } from "@/types";

const apiBaseUrl = (process.env.API_BASE_URL ?? "http://localhost:8000").replace(/\/$/, "");

async function backendFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${apiBaseUrl}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    cache: "no-store",
  });
  if (!response.ok) {
    const body = await response.text();
    throw new Error(`Backend request failed: ${response.status} ${response.statusText}${body ? ` - ${body}` : ""}`);
  }
  return (await response.json()) as T;
}

export const getDocuments = cache(async (): Promise<DocumentListResponse> => {
  return backendFetch<DocumentListResponse>("/api/documents");
});

export async function getSession(sessionId: string): Promise<SessionResponse> {
  return backendFetch<SessionResponse>(`/api/chat/sessions/${sessionId}`);
}
