import { getServerAuth } from "@/lib/supabase/server";

const apiBaseUrl = (process.env.API_BASE_URL ?? "http://localhost:8000").replace(/\/$/, "");


export async function POST(request: Request) {
  const { accessToken, authConfigured } = await getServerAuth();
  if (authConfigured && !accessToken) {
    return Response.json({ detail: "Authentication is required." }, { status: 401 });
  }
  const payload = await request.json();
  const response = await fetch(`${apiBaseUrl}/api/chat/ask`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(authConfigured && accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
    },
    body: JSON.stringify(payload),
  });
  const body = await response.text();
  return new Response(body, {
    status: response.status,
    headers: { "Content-Type": "application/json" },
  });
}
