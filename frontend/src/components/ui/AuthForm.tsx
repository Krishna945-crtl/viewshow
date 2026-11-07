"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { User } from "@/lib/types";

export default function AuthForm({ mode }: { mode: "login" | "register" }) {
  const router = useRouter();
  const next = useSearchParams().get("next") || "/home/";
  const setSession = useAuth((s) => s.setSession);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function submit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    setBusy(true);
    setErr(null);
    try {
      const body = Object.fromEntries(f.entries());
      const r = await api<{ access_token: string; refresh_token: string; user: User }>(`/auth/${mode}`, { body, auth: false });
      setSession({ access: r.access_token, refresh: r.refresh_token, user: r.user });
      router.replace(next.startsWith("/") ? next : "/home/");
    } catch (e) {
      setErr((e as ApiError).message);
    } finally {
      setBusy(false);
    }
  }

  const isLogin = mode === "login";
  return (
    <div className="min-h-[80dvh] grid place-items-center px-4">
      <form onSubmit={submit} className="glass rounded-3xl p-6 sm:p-8 w-full max-w-sm space-y-4" noValidate={false}>
        <div>
          <h1 className="text-2xl font-bold">{isLogin ? "Welcome back" : "Create your account"}</h1>
          <p className="text-sm text-muted mt-1">{isLogin ? "Sign in to hold seats and see your tickets." : "Takes ten seconds. No spam."}</p>
        </div>
        {!isLogin && (
          <label className="block text-sm">Full name
            <input name="full_name" required className="input mt-1" autoComplete="name" />
          </label>
        )}
        <label className="block text-sm">Email
          <input name="email" type="email" required className="input mt-1" autoComplete="email"
                 defaultValue={isLogin ? "demo@cineverse.dev" : ""} />
        </label>
        <label className="block text-sm">Password
          <input name="password" type="password" required minLength={8} className="input mt-1"
                 autoComplete={isLogin ? "current-password" : "new-password"} defaultValue={isLogin ? "Demo@1234" : ""} />
        </label>
        {!isLogin && <p className="text-xs text-muted -mt-2">At least 8 characters, mix letters and numbers.</p>}
        {err && <p className="text-sm text-red-400" role="alert">{err}</p>}
        <button className="btn btn-primary w-full" disabled={busy}>{busy ? "Please wait…" : isLogin ? "Sign in" : "Create account"}</button>
        <p className="text-sm text-center text-muted">
          {isLogin ? "New here? " : "Already have an account? "}
          <Link className="text-accent underline-offset-2 hover:underline" href={`/${isLogin ? "register" : "login"}/?next=${encodeURIComponent(next)}`}>
            {isLogin ? "Create an account" : "Sign in"}
          </Link>
        </p>
        {isLogin && <p className="text-[11px] text-center text-muted">Demo login is pre-filled · admin: admin@cineverse.dev / Admin@123</p>}
      </form>
    </div>
  );
}
