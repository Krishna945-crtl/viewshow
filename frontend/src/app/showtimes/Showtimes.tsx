"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import ThemeApplier from "@/components/ui/ThemeApplier";
import { DemoBadge, Empty, Spinner } from "@/components/ui/bits";
import { dayChip, rupees, showTime } from "@/lib/format";
import { usePrefs } from "@/lib/prefs";
import type { Movie, ShowSummary, TheatreInfo } from "@/lib/types";
import { useApi } from "@/lib/useApi";

interface Resp { movie: Movie; dates: string[]; theatres: { theatre: TheatreInfo; shows: ShowSummary[] }[] }

export default function Showtimes() {
  const slug = useSearchParams().get("movie");
  const city = usePrefs((p) => p.city);
  const setPrefs = usePrefs((p) => p.set);
  const [day, setDay] = useState<string | null>(null);
  const { data: cities } = useApi<{ city: string }[]>("/cities");
  const { data: all } = useApi<Resp>(slug ? `/movies/${slug}/showtimes?city=${encodeURIComponent(city)}` : null);
  const active = day ?? all?.dates[0] ?? null;
  const { data, loading } = useApi<Resp>(slug && active ? `/movies/${slug}/showtimes?city=${encodeURIComponent(city)}&date=${active}` : null);

  useEffect(() => setDay(null), [city]);
  const movie = all?.movie;

  return (
    <div className="mx-auto max-w-4xl px-4 py-6">
      <ThemeApplier theme={movie?.theme} />
      <Link href={`/movie/?id=${slug}`} className="text-sm text-muted hover:text-text">← {movie?.title ?? "Back"}</Link>
      <h1 className="text-2xl sm:text-3xl font-bold mt-2">Pick a show</h1>

      <div className="mt-4 flex gap-3 items-center">
        <label htmlFor="city2" className="text-sm text-muted">City</label>
        <select id="city2" className="input !w-auto" value={city} onChange={(e) => setPrefs({ city: e.target.value })}>
          {(cities ?? [{ city }]).map((c) => <option key={c.city}>{c.city}</option>)}
        </select>
      </div>

      {all && all.dates.length > 0 && (
        <div className="mt-4 flex gap-2 overflow-x-auto no-scrollbar pb-1" role="tablist" aria-label="Date">
          {all.dates.map((d) => {
            const c = dayChip(d);
            const on = d === active;
            return (
              <button key={d} role="tab" aria-selected={on} onClick={() => setDay(d)}
                className={`shrink-0 w-16 rounded-2xl py-2 text-center border transition ${on ? "bg-primary border-transparent text-white" : "border-line bg-white/5"}`}>
                <div className="text-[11px] uppercase opacity-80">{c.wd}</div>
                <div className="text-xl font-bold leading-tight">{c.day}</div>
                <div className="text-[11px] opacity-80">{c.mon}</div>
              </button>
            );
          })}
        </div>
      )}

      <div className="mt-6 space-y-4">
        {(loading && !data) || !all ? <Spinner label="Finding shows" /> :
          !data || data.theatres.length === 0 ? (
            <Empty title={`No shows in ${city}`} hint="Try a different city or date." />
          ) : (
            data.theatres.map(({ theatre, shows }) => (
              <article key={theatre.id} className="glass rounded-2xl p-4">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <h2 className="font-semibold">{theatre.name}</h2>
                    <p className="text-xs text-muted">{theatre.address}</p>
                    {!!theatre.amenities?.length && <p className="text-[11px] text-muted mt-1">{theatre.amenities.join(" · ")}</p>}
                  </div>
                  {theatre.is_demo && <DemoBadge />}
                </div>
                <div className="mt-3 flex flex-wrap gap-2">
                  {shows.map((s) => {
                    const from = Math.min(...Object.values(s.prices));
                    return (
                      <Link key={s.id} href={`/seats/?show=${s.id}`}
                        className="rounded-xl border border-line px-3 py-2 hover:border-accent transition min-w-24 text-center"
                        aria-label={`${showTime(s.starts_at)}, ${s.format}, ${s.auditorium.name}, from ${rupees(from)}`}>
                        <div className="font-semibold text-accent">{showTime(s.starts_at)}</div>
                        <div className="text-[10px] text-muted">{s.format} · {s.auditorium.name.split("·")[0].trim()}</div>
                        <div className="text-[10px] text-muted">from {rupees(from)}</div>
                      </Link>
                    );
                  })}
                </div>
              </article>
            ))
          )}
      </div>
    </div>
  );
}
