// Redirect hot-path load test. Run against the compose stack:
//   docker run --rm -i --network snapurl_default -e BASE=http://web grafana/k6:0.55.0 run - < loadtest/redirect.js
import http from "k6/http";
import { check } from "k6";

const BASE = __ENV.BASE || "http://localhost:8080";

export const options = {
  scenarios: {
    redirects: {
      executor: "constant-vus",
      vus: Number(__ENV.VUS || 50),
      duration: __ENV.DURATION || "30s",
    },
  },
  maxRedirects: 0,
  summaryTrendStats: ["avg", "med", "p(95)", "p(99)", "max"],
  thresholds: {
    checks: ["rate>0.999"],
    http_req_failed: ["rate<0.001"],
  },
};

export function setup() {
  const email = `load-${Date.now()}@example.com`;
  const reg = http.post(`${BASE}/api/auth/register`, JSON.stringify({ email, password: "password123" }), {
    headers: { "content-type": "application/json" },
  });
  const token = reg.json("access_token");
  const codes = [];
  for (let i = 0; i < 20; i++) {
    const r = http.post(`${BASE}/api/links`, JSON.stringify({ url: `https://example.com/page/${i}` }), {
      headers: { "content-type": "application/json", authorization: `Bearer ${token}` },
    });
    codes.push(r.json("code"));
  }
  return { codes };
}

const AGENTS = [
  "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36",
  "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1",
];
const COUNTRIES = ["IN", "US", "DE", "GB", "SG"];

export default function ({ codes }) {
  const code = codes[Math.floor(Math.random() * codes.length)];
  const res = http.get(`${BASE}/${code}`, {
    headers: {
      "user-agent": AGENTS[__ITER % AGENTS.length],
      "cf-ipcountry": COUNTRIES[__ITER % COUNTRIES.length],
      "x-forwarded-for": `10.0.${__VU % 255}.${__ITER % 255}`,
    },
    // Accept 302 as the expected status (k6 counts non-2xx/3xx as failed by default).
    responseCallback: http.expectedStatuses(302),
  });
  check(res, { "302 to target": (r) => r.status === 302 && r.headers["Location"].startsWith("https://example.com/") });
}
