import { getServerAuth } from "@/lib/supabase/server";

const apiBaseUrl = process.env.API_BASE_URL ?? "http://localhost:8000";


export async function GET() {
  const { accessToken, authConfigured } = await getServerAuth();
  if (authConfigured && !accessToken) {
    return Response.json({ detail: "Authentication is required." }, { status: 401 });
  }
  const response = await fetch(`${apiBaseUrl}/api/documents`, {
    cache: "no-store",
    headers: authConfigured && accessToken ? { Authorization: `Bearer ${accessToken}` } : undefined,
  });
  const body = await response.text();
  return new Response(body, {
    status: response.status,
    headers: { "Content-Type": "application/json" },
  });
}


export async function POST(request: Request) {
  const { accessToken, authConfigured } = await getServerAuth();
  if (authConfigured && !accessToken) {
    return Response.json({ detail: "Authentication is required." }, { status: 401 });
  }
  const formData = await request.formData();
  const response = await fetch(`${apiBaseUrl}/api/documents/upload`, {
    method: "POST",
    headers: authConfigured && accessToken ? { Authorization: `Bearer ${accessToken}` } : undefined,
    body: formData,
  });
  const body = await response.text();
  return new Response(body, {
    status: response.status,
    headers: { "Content-Type": "application/json" },
  });
}
