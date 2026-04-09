const apiBaseUrl = process.env.API_BASE_URL ?? "http://localhost:8000";


export async function POST(request: Request) {
  const payload = await request.json();
  const response = await fetch(`${apiBaseUrl}/api/chat/ask`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const body = await response.text();
  return new Response(body, {
    status: response.status,
    headers: { "Content-Type": "application/json" },
  });
}

