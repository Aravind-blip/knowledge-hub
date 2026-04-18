import http from "k6/http";
import { check, sleep } from "k6";
import { Rate, Trend } from "k6/metrics";

const BASE_URL = (__ENV.BASE_URL || "http://localhost:8000").replace(/\/$/, "");
const TOKEN = __ENV.K6_BEARER_TOKEN || "";
const SUPABASE_URL = (__ENV.SUPABASE_URL || "").replace(/\/$/, "");
const SUPABASE_ANON_KEY = __ENV.SUPABASE_ANON_KEY || "";
const LOGIN_EMAIL = __ENV.K6_LOGIN_EMAIL || "";
const LOGIN_PASSWORD = __ENV.K6_LOGIN_PASSWORD || "";
const ENABLE_UPLOAD = (__ENV.ENABLE_UPLOAD || "false").toLowerCase() === "true";
const UPLOAD_FILE_CONTENT = ENABLE_UPLOAD ? open("../../docs/demo-data/support_policy.md") : null;
const QUESTIONS = [
  "What are the escalation steps for a late shipment?",
  "What is the password reset turnaround time?",
  "When should a billing dispute be handed to finance?",
  "How often are control documents reviewed?",
  "What is the acknowledgment target for a priority one incident?",
];

export const queryLatency = new Trend("query_latency", true);
export const listLatency = new Trend("list_latency", true);
export const ingestionLatency = new Trend("ingestion_latency", true);
export const loginLatency = new Trend("login_latency", true);
export const requestErrors = new Rate("request_errors");
export const uploadSuccess = new Rate("upload_success");

const scenarios = {
  list_documents: {
    executor: "constant-vus",
    exec: "listDocuments",
    vus: Number(__ENV.LIST_VUS || 5),
    duration: __ENV.LIST_DURATION || "30s",
  },
  ask_queries_5: {
    executor: "constant-vus",
    exec: "askQuestion",
    vus: 5,
    duration: __ENV.QUERY_DURATION || "30s",
  },
  ask_queries_10: {
    executor: "constant-vus",
    exec: "askQuestion",
    vus: 10,
    duration: __ENV.QUERY_DURATION || "30s",
    startTime: __ENV.QUERY_10_START || "35s",
  },
};

if (SUPABASE_URL && SUPABASE_ANON_KEY && LOGIN_EMAIL && LOGIN_PASSWORD) {
  scenarios.login_users_5 = {
    executor: "constant-vus",
    exec: "loginUser",
    vus: Number(__ENV.LOGIN_VUS || 5),
    duration: __ENV.LOGIN_DURATION || "30s",
  };
}

if (ENABLE_UPLOAD) {
  scenarios.upload_documents = {
    executor: "shared-iterations",
    exec: "uploadDocument",
    vus: Number(__ENV.UPLOAD_VUS || 2),
    iterations: Number(__ENV.UPLOAD_ITERATIONS || 4),
    startTime: __ENV.UPLOAD_START || "70s",
    maxDuration: __ENV.UPLOAD_MAX_DURATION || "4m",
  };
}

export const options = {
  scenarios,
  thresholds: {
    request_errors: ["rate<0.05"],
    query_latency: ["p(95)<2500"],
    list_latency: ["p(95)<1200"],
    login_latency: ["p(95)<2500"],
  },
};

function authHeaders(contentType = "application/json") {
  const headers = {};
  if (contentType) {
    headers["Content-Type"] = contentType;
  }
  if (TOKEN) {
    headers.Authorization = `Bearer ${TOKEN}`;
  }
  return headers;
}

export function listDocuments() {
  const response = http.get(`${BASE_URL}/api/documents`, { headers: authHeaders(null) });
  listLatency.add(response.timings.duration);
  const ok = check(response, {
    "documents list returns success": (res) => res.status === 200,
  });
  requestErrors.add(!ok);
  sleep(1);
}

export function loginUser() {
  const response = http.post(
    `${SUPABASE_URL}/auth/v1/token?grant_type=password`,
    JSON.stringify({
      email: LOGIN_EMAIL,
      password: LOGIN_PASSWORD,
    }),
    {
      headers: {
        "Content-Type": "application/json",
        apikey: SUPABASE_ANON_KEY,
      },
    },
  );
  loginLatency.add(response.timings.duration);
  const ok = check(response, {
    "login returns success": (res) => res.status === 200,
    "login returns access token": (res) => {
      try {
        return Boolean(JSON.parse(res.body).access_token);
      } catch (_) {
        return false;
      }
    },
  });
  requestErrors.add(!ok);
  sleep(1);
}

export function askQuestion() {
  const question = QUESTIONS[Math.floor(Math.random() * QUESTIONS.length)];
  const response = http.post(
    `${BASE_URL}/api/chat/ask`,
    JSON.stringify({ question, session_id: null }),
    { headers: authHeaders() },
  );
  queryLatency.add(response.timings.duration);
  const ok = check(response, {
    "ask endpoint returns success": (res) => res.status === 200,
    "ask endpoint returns answer": (res) => {
      try {
        return Boolean(JSON.parse(res.body).answer);
      } catch (_) {
        return false;
      }
    },
  });
  requestErrors.add(!ok);
  sleep(1);
}

export function uploadDocument() {
  const payload = {
    file: http.file(UPLOAD_FILE_CONTENT, "support_policy.md", "text/markdown"),
  };
  const response = http.post(`${BASE_URL}/api/documents/upload`, payload, {
    headers: TOKEN ? { Authorization: `Bearer ${TOKEN}` } : undefined,
  });
  ingestionLatency.add(response.timings.duration);
  const ok = check(response, {
    "upload returns success": (res) => res.status === 201,
  });
  uploadSuccess.add(ok);
  requestErrors.add(!ok);
}

export function handleSummary(summary) {
  const queryValues = summary.metrics.query_latency?.values || {};
  const listValues = summary.metrics.list_latency?.values || {};
  const ingestionValues = summary.metrics.ingestion_latency?.values || {};
  const loginValues = summary.metrics.login_latency?.values || {};
  const metrics = {
    p50_login_latency_ms: loginValues["p(50)"] ?? loginValues.med ?? null,
    p95_login_latency_ms: loginValues["p(95)"] ?? null,
    p50_query_latency_ms: queryValues["p(50)"] ?? queryValues.med ?? null,
    p95_query_latency_ms: queryValues["p(95)"] ?? null,
    p50_list_latency_ms: listValues["p(50)"] ?? listValues.med ?? null,
    p95_list_latency_ms: listValues["p(95)"] ?? null,
    p50_ingestion_latency_ms: ingestionValues["p(50)"] ?? ingestionValues.med ?? null,
    p95_ingestion_latency_ms: ingestionValues["p(95)"] ?? null,
    error_rate: summary.metrics.request_errors?.values?.rate ?? null,
    throughput_rps: summary.metrics.http_reqs?.values?.rate ?? null,
    ingestion_success_rate: summary.metrics.upload_success?.values?.rate ?? null,
  };
  const artifact = JSON.stringify(
    {
      generated_at: new Date().toISOString(),
      metrics,
      scenarios: Object.keys(scenarios),
    },
    null,
    2,
  );
  return {
    "artifacts/load/latest.json": artifact,
    stdout:
      `Knowledge Hub load summary\n` +
      `- p95 login latency: ${metrics.p95_login_latency_ms ?? "n/a"} ms\n` +
      `- p95 query latency: ${metrics.p95_query_latency_ms ?? "n/a"} ms\n` +
      `- p95 list latency: ${metrics.p95_list_latency_ms ?? "n/a"} ms\n` +
      `- p95 ingestion latency: ${metrics.p95_ingestion_latency_ms ?? "n/a"} ms\n` +
      `- error rate: ${metrics.error_rate ?? "n/a"}\n` +
      `- throughput: ${metrics.throughput_rps ?? "n/a"} req/s\n`,
  };
}
