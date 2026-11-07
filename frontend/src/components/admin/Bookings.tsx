"use client";

import { useState } from "react";
import { Spinner } from "@/components/ui/bits";
import { toast } from "@/components/ui/toast";
import { api, ApiError } from "@/lib/api";
import { rupees, showDate, showTime } from "@/lib/format";
import type { Booking } from "@/lib/types";
import { useApi } from "@/lib/useApi";

export function Bookings() {
  const [status, setStatus] = useState("");
  const [q, setQ] = useState("");
  const { data, reload } = useApi<Booking[]>(`/admin/bookings?${status ? `status=${status}&` : ""}${q ? `q=${q}` : ""}`);
  const [payload, setPayload] = useState("");

  async function checkIn(e: React.FormEvent) {
    e.preventDefault();
    try {
      const r = await api<{ first_scan: boolean; booking: Booking }>("/admin/tickets/check-in", { body: { payload: payload.trim() } });
      toast(r.first_scan ? `✓ Valid · ${r.booking.reference} · seats ${r.booking.seats.map((s) => s.label).join(", ")}` : `Already scanned earlier · ${r.booking.reference}`, r.first_scan ? "success" : "info");
      setPayload("");
    } catch (err) { toast((err as ApiError).message, "error"); }
  }
  async function cancel(b: Booking) {
    if (!confirm(`Cancel ${b.reference}?`)) return;
    await api(`/admin/bookings/${b.id}/cancel`, { method: "POST" });
    reload();
  }
  return (
    <div className="space-y-4">
      <form onSubmit={checkIn} className="glass rounded-2xl p-4 flex gap-2">
        <input className="input" placeholder="Ticket check-in: paste/scan QR payload (CV3D|REF|sig)" value={payload} onChange={(e) => setPayload(e.target.value)} />
        <button className="btn btn-primary">Verify</button>
      </form>
      <div className="flex gap-2 flex-wrap">
        <input className="input !w-40" placeholder="Reference" value={q} onChange={(e) => setQ(e.target.value.toUpperCase())} />
        {["", "CONFIRMED", "PENDING_PAYMENT", "CANCELLED", "EXPIRED"].map((s) => (
          <button key={s} className="chip" aria-pressed={status === s} onClick={() => setStatus(s)}>{s ? s.replace("_", " ") : "All"}</button>
        ))}
      </div>
      {!data ? <Spinner /> : (
        <div className="glass rounded-2xl overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="text-xs text-muted text-left"><tr><th className="p-3 font-normal">Ref</th><th className="font-normal">Status</th><th className="font-normal">Movie / show</th><th className="font-normal">Seats</th><th className="font-normal">Amount</th><th /></tr></thead>
            <tbody>
              {data.map((b) => (
                <tr key={b.id} className="border-t border-line">
                  <td className="p-3 font-mono">{b.reference}</td>
                  <td className="text-xs">{b.status.replace("_", " ")}{b.checked_in_at ? " · in" : ""}</td>
                  <td className="text-xs">{b.movie.title}<div className="text-muted">{b.theatre.name} · {showDate(b.show.starts_at)} {showTime(b.show.starts_at)}</div></td>
                  <td className="text-xs">{b.seats.map((s) => s.label).join(", ")}</td>
                  <td>{rupees(b.amount_paise)}</td>
                  <td className="pr-3 text-right">{(b.status === "CONFIRMED" || b.status === "PENDING_PAYMENT") && <button className="text-xs text-red-300" onClick={() => cancel(b)}>Cancel</button>}</td>
                </tr>
              ))}
              {data.length === 0 && <tr><td className="p-6 text-muted text-center" colSpan={6}>No bookings.</td></tr>}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export function Errors() {
  const { data } = useApi<{ id: number; at: string; path: string; method: string; type: string; message: string; request_id: string }[]>("/admin/errors");
  if (!data) return <Spinner />;
  if (!data.length) return <p className="text-muted text-sm glass rounded-2xl p-6">No server errors recorded. 🎉</p>;
  return (
    <div className="space-y-2">
      {data.map((e) => (
        <article key={e.id} className="glass rounded-xl p-3 text-xs">
          <div className="flex gap-2"><span className="text-red-300 font-semibold">{e.type}</span><span className="text-muted">{e.method} {e.path}</span><span className="ml-auto text-muted">{new Date(e.at).toLocaleString()}</span></div>
          <p className="mt-1 font-mono break-all">{e.message}</p>
          <p className="text-muted mt-1">request {e.request_id}</p>
        </article>
      ))}
    </div>
  );
}
