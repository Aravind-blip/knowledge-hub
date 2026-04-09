const apiBaseUrl = process.env.API_BASE_URL ?? "http://localhost:8000";


export async function GET() {
  const response = await fetch(`${apiBaseUrl}/api/documents`, { cache: "no-store" });
  const body = await response.text();
  return new Response(body, {
    status: response.status,
    headers: { "Content-Type": "application/json" },
  });
}


export async function POST(request: Request) {
  const formData = await request.formData();
  const response = await fetch(`${apiBaseUrl}/api/documents/upload`, {
    method: "POST",
    body: formData,
  });
  const body = await response.text();
  return new Response(body, {
    status: response.status,
    headers: { "Content-Type": "application/json" },
  });
}

