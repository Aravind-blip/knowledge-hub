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

export async function getDocuments(): Promise<DocumentListResponse> {
  return backendFetch<DocumentListResponse>("/api/documents");
}

export async function getSession(sessionId: string): Promise<SessionResponse> {
  return backendFetch<SessionResponse>(`/api/chat/sessions/${sessionId}`);
}

export async function getSessions(): Promise<SessionListResponse> {
  return backendFetch<SessionListResponse>("/api/chat/sessions");
}

export async function getWorkspaceSummary(): Promise<WorkspaceSummary> {
  return backendFetch<WorkspaceSummary>("/api/workspace/summary");
}
