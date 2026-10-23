export type User = { id: number; email: string; created_at: string };

export type Link = {
  id: number;
  code: string;
  short_url: string;
  target_url: string;
  title: string | null;
  is_active: boolean;
  expires_at: string | null;
  click_count: number;
  created_at: string;
  updated_at: string;
};

export type LinkPage = { items: Link[]; total: number; page: number; page_size: number };
export type CountRow = { key: string; count: number };
export type DayRow = { date: string; clicks: number; visitors: number };

export type LinkStats = {
  link_id: number;
  days: number;
  total_clicks: number;
  unique_visitors: number;
  bot_clicks: number;
  timeseries: DayRow[];
  countries: CountRow[];
  devices: CountRow[];
  browsers: CountRow[];
  os: CountRow[];
  referrers: CountRow[];
};

export type Overview = {
  total_links: number;
  active_links: number;
  total_clicks: number;
  clicks_last_7d: number;
  timeseries: DayRow[];
  top_links: Link[];
};

type TokenResponse = { access_token: string; expires_in: number; user: User };

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

// The access token lives only in memory; the refresh token is an httpOnly cookie
// the page can't read, so XSS can't exfiltrate a long-lived credential.
let accessToken: string | null = null;
let refreshing: Promise<User | null> | null = null;
let onSessionLost: (() => void) | null = null;

export function setSessionLostHandler(fn: () => void) {
  onSessionLost = fn;
}

async function errorFrom(res: Response): Promise<ApiError> {
  let message = res.statusText || "Request failed";
  try {
    const body = await res.json();
    if (typeof body.detail === "string") message = body.detail;
    else if (Array.isArray(body.detail) && body.detail[0]?.msg) {
      message = body.detail.map((d: { msg: string }) => d.msg.replace(/^Value error, /, "")).join("; ");
    }
  } catch {
    /* non-JSON error body */
  }
  if (res.status === 429) {
    const wait = res.headers.get("retry-after");
    if (wait) message = `${message} (try again in ${wait}s)`;
  }
  return new ApiError(res.status, message);
}

/** Exchanges the refresh cookie for a new access token. Concurrent callers share one request. */
export function refreshSession(): Promise<User | null> {
  refreshing ??= fetch("/api/auth/refresh", { method: "POST", credentials: "include" })
    .then(async (res) => {
      if (!res.ok) {
        accessToken = null;
        return null;
      }
      const data: TokenResponse = await res.json();
      accessToken = data.access_token;
      return data.user;
    })
    .catch(() => null)
    .finally(() => {
      refreshing = null;
    });
  return refreshing;
}

export async function api<T>(path: string, init: RequestInit = {}, retry = true): Promise<T> {
  const headers = new Headers(init.headers);
  if (init.body && !headers.has("content-type")) headers.set("content-type", "application/json");
  if (accessToken) headers.set("authorization", `Bearer ${accessToken}`);

  const res = await fetch(path, { ...init, headers, credentials: "include" });
  if (res.status === 401 && retry && !path.startsWith("/api/auth/")) {
    if (await refreshSession()) return api<T>(path, init, false);
    onSessionLost?.();
  }
  if (!res.ok) throw await errorFrom(res);
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

async function authenticate(path: string, email: string, password: string): Promise<User> {
  const data = await api<TokenResponse>(path, { method: "POST", body: JSON.stringify({ email, password }) });
  accessToken = data.access_token;
  return data.user;
}

export const auth = {
  login: (email: string, password: string) => authenticate("/api/auth/login", email, password),
  register: (email: string, password: string) => authenticate("/api/auth/register", email, password),
  async logout() {
    try {
      await api("/api/auth/logout", { method: "POST" });
    } finally {
      accessToken = null;
    }
  },
};

export type LinkInput = { url: string; alias?: string; title?: string; expires_at?: string | null };
export type LinkPatch = Partial<{ url: string; title: string | null; is_active: boolean; expires_at: string | null }>;

export const links = {
  list: (params: { q?: string; page?: number; page_size?: number; sort?: "recent" | "clicks" }) => {
    const qs = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => v !== undefined && v !== "" && qs.set(k, String(v)));
    return api<LinkPage>(`/api/links?${qs}`);
  },
  get: (id: number) => api<Link>(`/api/links/${id}`),
  create: (body: LinkInput) => api<Link>("/api/links", { method: "POST", body: JSON.stringify(body) }),
  update: (id: number, body: LinkPatch) =>
    api<Link>(`/api/links/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
  remove: (id: number) => api<void>(`/api/links/${id}`, { method: "DELETE" }),
  stats: (id: number, days: number) => api<LinkStats>(`/api/links/${id}/stats?days=${days}`),
  overview: (days: number) => api<Overview>(`/api/stats/overview?days=${days}`),
};
