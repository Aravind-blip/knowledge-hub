import { getServerAuth } from "@/lib/supabase/server";

const apiBaseUrl = (process.env.API_BASE_URL ?? "http://localhost:8000").replace(/\/$/, "");

export async function GET(_: Request, { params }: { params: Promise<{ sessionId: string }> }) {
  const { accessToken, authConfigured } = await getServerAuth();
  if (authConfigured && !accessToken) {
    return Response.json({ detail: "Authentication is required." }, { status: 401 });
  }
  const { sessionId } = await params;
  const response = await fetch(`${apiBaseUrl}/api/chat/sessions/${sessionId}`, {
    cache: "no-store",
    headers: authConfigured && accessToken ? { Authorization: `Bearer ${accessToken}` } : {},
  });
  const body = await response.text();
  return new Response(body, {
    status: response.status,
    headers: { "Content-Type": "application/json" },
  });
}
