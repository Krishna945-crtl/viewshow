"use client";

import { Spinner, Stat } from "@/components/ui/bits";
import { rupees, showDate, showTime } from "@/lib/format";
import { useApi } from "@/lib/useApi";

interface Stats {
  revenue_paise: number; tickets_sold: number; refunds_pending: number; upcoming_shows: number; errors_24h: number;
  bookings_by_status: Record<string, number>;
  occupancy: { show_id: string; movie: string; theatre: string; starts_at: string; sold: number; capacity: number; occupancy: number }[];
  revenue_by_movie: { movie: string; revenue_paise: number }[];
}

// single-series magnitude -> one hue, thin bars, value in text ink, rows double as the table view
function Bar({ value, max, label }: { value: number; max: number; label: string }) {
  const pct = max ? Math.max(1.5, (value / max) * 100) : 0;
  return (
    <div className="h-2.5 w-full rounded-full bg-white/5" title={label}>
      <div className="h-full rounded-full" style={{ width: `${pct}%`, background: "#5b8def" }} />
    </div>
  );
}

export default function Overview() {
  const { data: s, loading } = useApi<Stats>("/admin/stats");
  if (loading || !s) return <Spinner />;
  const maxRev = Math.max(1, ...s.revenue_by_movie.map((r) => r.revenue_paise));
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-3">
        <Stat label="Revenue (confirmed)" value={rupees(s.revenue_paise)} />
        <Stat label="Tickets sold" value={s.tickets_sold} />
        <Stat label="Upcoming shows" value={s.upcoming_shows} />
        <Stat label="Refunds pending" value={s.refunds_pending} />
        <Stat label="Errors (24h)" value={<span className={s.errors_24h ? "text-red-300" : ""}>{s.errors_24h}</span>} />
      </div>
      <div className="flex flex-wrap gap-2 text-xs">
        {Object.entries(s.bookings_by_status).map(([k, v]) => <span key={k} className="chip">{k.replace("_", " ")}: {v}</span>)}
      </div>
      <div className="grid lg:grid-cols-2 gap-4">
        <section className="glass rounded-2xl p-4">
          <h2 className="font-semibold">Highest occupancy · upcoming</h2>
          <table className="w-full text-sm mt-3">
            <thead className="text-xs text-muted text-left"><tr><th className="font-normal pb-2">Show</th><th className="font-normal pb-2 w-1/3">Fill</th><th className="font-normal pb-2 text-right">Sold</th></tr></thead>
            <tbody>
              {s.occupancy.slice(0, 10).map((o) => (
                <tr key={o.show_id} className="border-t border-line">
                  <td className="py-2 pr-2"><div className="truncate max-w-48">{o.movie}</div><div className="text-[11px] text-muted truncate">{o.theatre} · {showDate(o.starts_at)} {showTime(o.starts_at)}</div></td>
                  <td className="pr-2"><Bar value={o.occupancy} max={1} label={`${Math.round(o.occupancy * 100)}% full`} /></td>
                  <td className="text-right tabular-nums">{o.sold}/{o.capacity}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
        <section className="glass rounded-2xl p-4">
          <h2 className="font-semibold">Revenue by movie</h2>
          {s.revenue_by_movie.length === 0 ? <p className="text-sm text-muted mt-3">No confirmed bookings yet.</p> : (
            <table className="w-full text-sm mt-3">
              <tbody>
                {s.revenue_by_movie.map((r) => (
                  <tr key={r.movie} className="border-t border-line first:border-0">
                    <td className="py-2 pr-2 truncate max-w-40">{r.movie}</td>
                    <td className="w-1/2 pr-2"><Bar value={r.revenue_paise} max={maxRev} label={rupees(r.revenue_paise)} /></td>
                    <td className="text-right tabular-nums">{rupees(r.revenue_paise)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </section>
      </div>
    </div>
  );
}
