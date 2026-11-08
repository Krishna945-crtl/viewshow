"use client";

import { useAuth } from "./auth";

export const API_BASE = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api").replace(/\/$/, "");
export const WS_BASE = API_BASE.replace(/^http/, "ws");
// uploaded posters live on the API host (/media/...), not on the site host
const API_ORIGIN = API_BASE.replace(/\/api$/, "");

export function assetUrl(url: string | null | undefined): string | null {
  if (!url) return null;
  return url.startsWith("/media/") ? `${API_ORIGIN}${url}` : url;
}

export class ApiError extends Error {
  constructor(public status: number, public code: string, message: string, public extra: Record<string, unknown> = {}) {
    super(message);
  }
}

let refreshing: Promise<boolean> | null = null;

async function refreshSession(): Promise<boolean> {
  const s = useAuth.getState().session;
  if (!s) return false;
  // several requests can 401 at once - only refresh once
  refreshing ??= (async () => {
    try {
      const r = await fetch(`${API_BASE}/auth/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: s.refresh }),
      });
      if (!r.ok) {
        useAuth.getState().setSession(null);
        return false;
      }
      const body = await r.json();
      useAuth.getState().setSession({ access: body.access_token, refresh: body.refresh_token, user: body.user });
      return true;
    } catch {
      return false;
    } finally {
      setTimeout(() => (refreshing = null), 0);
    }
  })();
  return refreshing;
}

type Opts = { method?: string; body?: unknown; auth?: boolean; retry?: boolean };

export async function api<T = unknown>(path: string, opts: Opts = {}): Promise<T> {
  const token = useAuth.getState().session?.access;
  const headers: Record<string, string> = { Accept: "application/json" };
  const isForm = typeof FormData !== "undefined" && opts.body instanceof FormData;
  // multipart: the browser writes its own boundary header
  if (opts.body !== undefined && !isForm) headers["Content-Type"] = "application/json";
  if (token && opts.auth !== false) headers.Authorization = `Bearer ${token}`;

  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, {
      method: opts.method ?? (opts.body !== undefined ? "POST" : "GET"),
      headers,
      body: isForm ? (opts.body as FormData) : opts.body !== undefined ? JSON.stringify(opts.body) : undefined,
    });
  } catch {
    throw new ApiError(0, "network", "Can't reach the server. Check your connection.");
  }

  if (res.status === 401 && token && opts.retry !== false && (await refreshSession())) {
    return api<T>(path, { ...opts, retry: false });
  }
  if (res.status === 204) return undefined as T;

  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const d = data?.detail ?? {};
    const msg = typeof d === "string" ? d : d.message ?? "Something went wrong";
    throw new ApiError(res.status, d.code ?? "error", msg, d);
  }
  return data as T;
}

export async function logout() {
  const s = useAuth.getState().session;
  if (s) api("/auth/logout", { body: { refresh_token: s.refresh }, auth: false }).catch(() => {});
  useAuth.getState().setSession(null);
}
