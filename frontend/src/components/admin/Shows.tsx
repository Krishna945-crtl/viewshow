"use client";

import { useState } from "react";
import { Spinner } from "@/components/ui/bits";
import { toast } from "@/components/ui/toast";
import { api, ApiError } from "@/lib/api";
import { rupees, showDate, showTime } from "@/lib/format";
import type { Movie, ShowSummary, TheatreInfo } from "@/lib/types";
import { useApi } from "@/lib/useApi";

type Row = ShowSummary & { movie_title: string; theatre: string };

export default function Shows() {
  const { data: shows, reload } = useApi<Row[]>("/admin/shows");
  const { data: movies } = useApi<Movie[]>("/admin/movies");
  const { data: theatres } = useApi<(TheatreInfo & { auditoriums: { id: string; name: string }[] })[]>("/theatres");
  const [form, setForm] = useState({ movie_id: "", auditorium_id: "", starts_at: "", format: "2D", language: "English", standard: 200, premium: 300, vip: 450, recliner: 600 });

  async function create(e: React.FormEvent) {
    e.preventDefault();
    const { standard, premium, vip, recliner, ...rest } = form;
    try {
      await api("/admin/shows", { body: { ...rest, starts_at: new Date(form.starts_at).toISOString(),
        prices: { standard: standard * 100, premium: premium * 100, vip: vip * 100, recliner: recliner * 100 } } });
      toast("Show scheduled", "success");
      reload();
    } catch (err) { toast((err as ApiError).message, "error"); }
  }
  async function cancel(id: string) {
    if (!confirm("Cancel this show? All its bookings are cancelled and flagged for refund.")) return;
    const r = await api<{ cancelled_bookings: number }>(`/admin/shows/${id}/cancel`, { method: "POST" });
    toast(`Show cancelled · ${r.cancelled_bookings} bookings released`);
    reload();
  }
  if (!shows) return <Spinner />;
  const num = (k: "standard" | "premium" | "vip" | "recliner") => (
    <label className="text-xs capitalize">{k} ₹<input type="number" min={0} className="input mt-1 !py-1.5" value={form[k]} onChange={(e) => setForm({ ...form, [k]: Number(e.target.value) })} /></label>
  );
  return (
    <div className="space-y-4">
      <form onSubmit={create} className="glass rounded-2xl p-4 grid sm:grid-cols-3 lg:grid-cols-6 gap-2 text-sm items-end">
        <label className="text-xs sm:col-span-2">Movie<select required className="input mt-1" value={form.movie_id} onChange={(e) => setForm({ ...form, movie_id: e.target.value })}><option value="">Select…</option>{movies?.filter((m) => m.is_active).map((m) => <option key={m.id} value={m.id}>{m.title}</option>)}</select></label>
        <label className="text-xs sm:col-span-2">Auditorium<select required className="input mt-1" value={form.auditorium_id} onChange={(e) => setForm({ ...form, auditorium_id: e.target.value })}><option value="">Select…</option>{theatres?.flatMap((t) => t.auditoriums.map((a) => <option key={a.id} value={a.id}>{t.name} · {a.name}</option>))}</select></label>
        <label className="text-xs sm:col-span-2">Starts<input required type="datetime-local" className="input mt-1" value={form.starts_at} onChange={(e) => setForm({ ...form, starts_at: e.target.value })} /></label>
        <label className="text-xs">Format<input className="input mt-1 !py-1.5" value={form.format} onChange={(e) => setForm({ ...form, format: e.target.value })} /></label>
        {num("standard")}{num("premium")}{num("vip")}{num("recliner")}
        <button className="btn btn-primary">Schedule</button>
      </form>
      <div className="glass rounded-2xl overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="text-xs text-muted text-left"><tr><th className="p-3 font-normal">When</th><th className="font-normal">Movie</th><th className="font-normal">Venue</th><th className="font-normal">Prices</th><th /></tr></thead>
          <tbody>
            {shows.slice(0, 150).map((s) => (
              <tr key={s.id} className={`border-t border-line ${s.is_cancelled ? "opacity-40" : ""}`}>
                <td className="p-3 whitespace-nowrap">{showDate(s.starts_at)} {showTime(s.starts_at)}</td>
                <td>{s.movie_title}</td>
                <td className="text-xs text-muted">{s.theatre} · {s.auditorium.name}</td>
                <td className="text-xs text-muted">{Object.entries(s.prices).map(([k, v]) => `${k} ${rupees(v)}`).join(" · ")}</td>
                <td className="pr-3 text-right">{!s.is_cancelled && <button className="text-xs text-red-300" onClick={() => cancel(s.id)}>Cancel</button>}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
