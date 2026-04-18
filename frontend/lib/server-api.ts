import { cache } from "react";

import type { DocumentListResponse, SessionListResponse, SessionResponse, WorkspaceSummary } from "@/types";
import { getServerAuth } from "@/lib/supabase/server";

const apiBaseUrl = (process.env.API_BASE_URL ?? "http://localhost:8000").replace(/\/$/, "");

async function backendFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const { accessToken, authConfigured } = await getServerAuth();
  const response = await fetch(`${apiBaseUrl}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(authConfigured && accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
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

export const getDocuments = cache(async function getDocuments(page = 1, pageSize = 20): Promise<DocumentListResponse> {
  const query = new URLSearchParams({
    page: String(page),
    page_size: String(pageSize),
  });
  return backendFetch<DocumentListResponse>(`/api/documents?${query.toString()}`);
});

export const getSession = cache(async function getSession(sessionId: string): Promise<SessionResponse> {
  return backendFetch<SessionResponse>(`/api/chat/sessions/${sessionId}`);
});

export const getSessions = cache(async function getSessions(page = 1, pageSize = 20): Promise<SessionListResponse> {
  const query = new URLSearchParams({
    page: String(page),
    page_size: String(pageSize),
  });
  return backendFetch<SessionListResponse>(`/api/chat/sessions?${query.toString()}`);
});

export const getWorkspaceSummary = cache(async function getWorkspaceSummary(): Promise<WorkspaceSummary> {
  return backendFetch<WorkspaceSummary>("/api/workspace/summary");
});
