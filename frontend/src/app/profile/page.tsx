"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Empty, Spinner } from "@/components/ui/bits";
import { toast } from "@/components/ui/toast";
import { api, ApiError, logout } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { rupees, showDate, showTime } from "@/lib/format";
import { usePrefs } from "@/lib/prefs";
import type { Booking } from "@/lib/types";
import { useApi } from "@/lib/useApi";

const BADGE: Record<string, string> = {
  CONFIRMED: "text-green-300 border-green-400/40", PENDING_PAYMENT: "text-amber-300 border-amber-400/40",
  EXPIRED: "text-muted border-line", CANCELLED: "text-muted border-line", FAILED: "text-red-300 border-red-400/40",
};

export default function Profile() {
  const router = useRouter();
  const { session, ready } = useAuth();
  const prefs = usePrefs();
  const { data, loading, reload } = useApi<Booking[]>(session ? "/bookings" : null);
  const [tab, setTab] = useState<"upcoming" | "past">("upcoming");
  const [now] = useState(() => Date.now());

  useEffect(() => {
    if (ready && !session) router.replace("/login/?next=/profile/");
  }, [ready, session, router]);
  if (!session) return <Spinner />;

  const list = (data ?? []).filter((b) => (tab === "upcoming" ? new Date(b.show.starts_at).getTime() > now : new Date(b.show.starts_at).getTime() <= now));

  async function cancel(b: Booking) {
    if (!confirm(`Cancel booking ${b.reference}? Seats ${b.seats.map((s) => s.label).join(", ")} will be released.`)) return;
    try {
      await api(`/bookings/${b.id}/cancel`, { method: "POST" });
      toast("Booking cancelled. Refund marked for processing (sandbox).", "success");
      reload();
    } catch (e) {
      toast((e as ApiError).message, "error");
    }
  }

  return (
    <div className="mx-auto max-w-3xl px-4 py-6">
      <section className="glass rounded-3xl p-5 flex items-center gap-4">
        <span className="size-14 rounded-full bg-primary grid place-items-center text-2xl font-bold">{session.user.full_name.charAt(0)}</span>
        <div className="min-w-0 flex-1">
          <h1 className="text-xl font-bold truncate">{session.user.full_name}</h1>
          <p className="text-sm text-muted truncate">{session.user.email}</p>
        </div>
        <button className="btn btn-ghost" onClick={() => { logout(); router.replace("/home/"); }}>Sign out</button>
      </section>

      <section className="mt-4 glass rounded-2xl p-4 flex flex-wrap gap-2 text-xs" aria-label="Accessibility and display">
        <button className="chip" aria-pressed={prefs.viewMode === "2d"} onClick={() => prefs.set({ viewMode: prefs.viewMode === "2d" ? "3d" : "2d" })}>Prefer 2D seat map</button>
        <button className="chip" aria-pressed={prefs.reduceMotion} onClick={() => prefs.set({ reduceMotion: !prefs.reduceMotion })}>Reduce motion</button>
        <button className="chip" aria-pressed={prefs.highContrast} onClick={() => prefs.set({ highContrast: !prefs.highContrast })}>High contrast</button>
      </section>

      <div className="mt-6 flex gap-2" role="tablist">
        {(["upcoming", "past"] as const).map((t) => (
          <button key={t} role="tab" aria-selected={tab === t} className={`chip capitalize ${tab === t ? "active" : ""}`} onClick={() => setTab(t)}>{t}</button>
        ))}
      </div>
      <div className="mt-4 space-y-3">
        {loading && !data ? <Spinner /> : list.length === 0 ? (
          <Empty title={tab === "upcoming" ? "No upcoming tickets" : "No past bookings"} hint="Your bookings show up here.">
            <Link href="/home/" className="btn btn-primary">Browse movies</Link>
          </Empty>
        ) : list.map((b) => (
          <article key={b.id} className="glass rounded-2xl p-4 flex flex-col sm:flex-row sm:items-center gap-3">
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <h2 className="font-semibold truncate">{b.movie.title}</h2>
                <span className={`text-[10px] border rounded-full px-2 py-0.5 ${BADGE[b.status]}`}>{b.status.replace("_", " ")}</span>
              </div>
              <p className="text-xs text-muted">{showDate(b.show.starts_at)} {showTime(b.show.starts_at)} · {b.theatre.name}</p>
              <p className="text-xs text-muted">Seats {b.seats.map((s) => s.label).join(", ")} · {rupees(b.amount_paise)} · Ref {b.reference}</p>
            </div>
            <div className="flex gap-2">
              {b.status === "CONFIRMED" && <Link className="btn btn-primary !min-h-9 !py-1.5 text-sm" href={`/ticket/?booking=${b.id}`}>Ticket</Link>}
              {b.status === "PENDING_PAYMENT" && <Link className="btn btn-primary !min-h-9 !py-1.5 text-sm" href={`/checkout/?booking=${b.id}`}>Pay</Link>}
              {(b.status === "CONFIRMED" || b.status === "PENDING_PAYMENT") && tab === "upcoming" && (
                <button className="btn btn-ghost !min-h-9 !py-1.5 text-sm" onClick={() => cancel(b)}>Cancel</button>
              )}
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}
