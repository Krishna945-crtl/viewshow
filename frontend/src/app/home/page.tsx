"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import MovieCard from "@/components/ui/MovieCard";
import PosterArt from "@/components/ui/PosterArt";
import ThemeApplier from "@/components/ui/ThemeApplier";
import { Empty, Spinner } from "@/components/ui/bits";
import { usePrefs } from "@/lib/prefs";
import type { Movie } from "@/lib/types";
import { useApi } from "@/lib/useApi";
import { runtime } from "@/lib/format";

export default function Home() {
  const city = usePrefs((p) => p.city);
  const setPrefs = usePrefs((p) => p.set);
  const [q, setQ] = useState("");
  const [genre, setGenre] = useState<string | null>(null);
  const [lang, setLang] = useState<string | null>(null);
  const [hover, setHover] = useState<Movie | null>(null);

  const { data: cities } = useApi<{ city: string; theatres: number }[]>("/cities");
  const { data: genres } = useApi<string[]>("/genres");
  const { data: movies, loading, error, reload } = useApi<Movie[]>(`/movies?city=${encodeURIComponent(city)}`);

  const list = useMemo(() => {
    let m = movies ?? [];
    if (q.trim()) m = m.filter((x) => x.title.toLowerCase().includes(q.trim().toLowerCase()));
    if (genre) m = m.filter((x) => x.genres.includes(genre));
    if (lang) m = m.filter((x) => x.language === lang);
    return m;
  }, [movies, q, genre, lang]);
  const languages = useMemo(() => [...new Set((movies ?? []).map((m) => m.language))].sort(), [movies]);
  const featured = hover ?? list[0] ?? null;

  return (
    <div className="mx-auto max-w-6xl px-4">
      <ThemeApplier theme={featured?.theme} />
      {featured && (
        <section className="relative mt-4 rounded-3xl overflow-hidden border border-line min-h-56 sm:min-h-72">
          <PosterArt movie={featured} className="absolute inset-0 w-full h-full scale-125 blur-sm opacity-60" />
          <div className="absolute inset-0 bg-gradient-to-r from-bg via-bg/80 to-transparent" />
          <div className="relative p-6 sm:p-10 max-w-xl">
            <p className="text-xs uppercase tracking-[0.2em] text-accent">Now showing in {city}</p>
            <h1 className="text-3xl sm:text-5xl font-bold mt-2 leading-tight">{featured.title}</h1>
            <p className="text-muted mt-2 line-clamp-2">{featured.tagline}</p>
            <p className="text-xs mt-3 text-muted">
              {featured.language} · {runtime(featured.runtime_minutes)} · Atmosphere: <span className="text-text">{featured.theme.mood || featured.theme.name}</span>
            </p>
            <div className="mt-5 flex gap-2">
              <Link href={`/showtimes/?movie=${featured.slug}`} className="btn btn-primary">Book seats</Link>
              <Link href={`/movie/?id=${featured.slug}`} className="btn btn-ghost">Details</Link>
            </div>
          </div>
        </section>
      )}

      <section className="mt-6 flex flex-col sm:flex-row gap-3 sm:items-center">
        <label className="sr-only" htmlFor="city">City</label>
        <select id="city" className="input sm:!w-48" value={city} onChange={(e) => setPrefs({ city: e.target.value })}>
          {(cities ?? [{ city, theatres: 0 }]).map((c) => <option key={c.city} value={c.city}>{c.city}</option>)}
        </select>
        <input className="input" placeholder="Search movies" value={q} onChange={(e) => setQ(e.target.value)} aria-label="Search movies" />
      </section>
      <div className="mt-3 flex gap-2 overflow-x-auto no-scrollbar pb-1" role="group" aria-label="Filter by genre">
        <button className="chip" aria-pressed={!genre} onClick={() => setGenre(null)}>All</button>
        {(genres ?? []).map((g) => (
          <button key={g} className="chip" aria-pressed={genre === g} onClick={() => setGenre(genre === g ? null : g)}>{g}</button>
        ))}
      </div>
      <div className="mt-2 flex gap-2 overflow-x-auto no-scrollbar pb-1" role="group" aria-label="Filter by language">
        {languages.map((l) => (
          <button key={l} className="chip" aria-pressed={lang === l} onClick={() => setLang(lang === l ? null : l)}>{l}</button>
        ))}
      </div>

      <section className="mt-6" aria-live="polite">
        {loading && !movies ? <Spinner label="Loading movies" /> : error ? (
          <Empty title="Couldn't load movies" hint={error.message}><button className="btn btn-ghost" onClick={reload}>Retry</button></Empty>
        ) : list.length === 0 ? (
          <Empty title="Nothing matches" hint={`No shows for that filter in ${city}. Try another city or genre.`} />
        ) : (
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4 sm:gap-6">
            {list.map((m) => <MovieCard key={m.id} movie={m} onHover={setHover} />)}
          </div>
        )}
      </section>
    </div>
  );
}
