"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { rupees } from "@/lib/format";
import { useSeats } from "@/lib/seats";
import type { RecOption } from "@/lib/types";

export default function Recommendations({ showId, onPreview, onClose }: { showId: string; onPreview: (id: string) => void; onClose: () => void }) {
  const [size, setSize] = useState(2);
  const [budget, setBudget] = useState<number | "">("");
  const [opts, setOpts] = useState<RecOption[] | null>(null);
  const [busy, setBusy] = useState(false);

  async function find() {
    setBusy(true);
    try {
      const r = await api<{ options: RecOption[] }>(`/shows/${showId}/recommendations`, {
        body: { group_size: size, max_price_per_seat: budget === "" ? null : budget * 100 },
      });
      setOpts(r.options);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="glass rounded-2xl p-4 w-full sm:w-80 shadow-2xl" aria-label="Seat recommendations">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold">Best seats for you</h3>
        <button onClick={onClose} className="text-muted text-lg" aria-label="Close">×</button>
      </div>
      <p className="text-xs text-muted mt-1">Ranked by screen centring, viewing angle and distance.</p>
      <div className="flex gap-2 mt-3 items-end">
        <label className="text-xs flex-1">People
          <select className="input mt-1 !py-1.5" value={size} onChange={(e) => setSize(Number(e.target.value))}>
            {Array.from({ length: 10 }, (_, i) => i + 1).map((n) => <option key={n}>{n}</option>)}
          </select>
        </label>
        <label className="text-xs flex-1">Max ₹/seat
          <input className="input mt-1 !py-1.5" inputMode="numeric" placeholder="Any" value={budget}
                 onChange={(e) => setBudget(e.target.value === "" ? "" : Number(e.target.value.replace(/\D/g, "")))} />
        </label>
        <button className="btn btn-primary !px-4" onClick={find} disabled={busy}>{busy ? "…" : "Find"}</button>
      </div>
      {opts && (
        <ul className="mt-3 space-y-2 max-h-64 overflow-auto">
          {opts.length === 0 && <li className="text-sm text-muted">No matching seats left — try a bigger budget or smaller group.</li>}
          {opts.map((o) => (
            <li key={o.seat_ids.join()} className="rounded-xl border border-line p-3">
              <div className="flex justify-between text-sm">
                <span className="font-semibold">{o.labels.join(", ")}</span>
                <span className="text-accent font-semibold">{o.score}</span>
              </div>
              <p className="text-[11px] text-muted mt-0.5">{o.reasons.join(" · ")} · {rupees(o.total_paise)}</p>
              <div className="flex gap-2 mt-2">
                <button className="btn btn-ghost !min-h-8 !py-1 text-xs flex-1" onClick={() => onPreview(o.seat_ids[Math.floor(o.seat_ids.length / 2)])}>👁 Preview</button>
                <button className="btn btn-primary !min-h-8 !py-1 text-xs flex-1" onClick={() => useSeats.getState().holdMany(o.seat_ids)}>Pick these</button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
