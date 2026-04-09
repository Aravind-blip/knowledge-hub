const apiBaseUrl = process.env.API_BASE_URL ?? "http://localhost:8000";


export async function GET(_: Request, { params }: { params: Promise<{ sessionId: string }> }) {
  const { sessionId } = await params;
  const response = await fetch(`${apiBaseUrl}/api/chat/sessions/${sessionId}`, { cache: "no-store" });
  const body = await response.text();
  return new Response(body, {
    status: response.status,
    headers: { "Content-Type": "application/json" },
  });
}

