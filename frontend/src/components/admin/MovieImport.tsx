"use client";

import { useState } from "react";
import { toast } from "@/components/ui/toast";
import { api, ApiError } from "@/lib/api";
import type { Movie, TmdbHit } from "@/lib/types";
import { useApi } from "@/lib/useApi";

/** Search TMDB and pull any real film in with one click. Its theme is generated on the spot. */
export default function MovieImport({ onImported }: { onImported: (m: Movie) => void }) {
  const { data: status } = useApi<{ enabled: boolean }>("/admin/tmdb/status");
  const [q, setQ] = useState("");
  const [hits, setHits] = useState<TmdbHit[] | null>(null);
  const [busy, setBusy] = useState<number | "search" | null>(null);

  if (!status) return null;
  if (!status.enabled) {
    return (
      <div className="glass rounded-2xl p-4 text-sm">
        <p className="font-semibold">Import any real movie</p>
        <p className="text-muted mt-1">
          Add a free TMDB key as <code className="text-text">CV_TMDB_API_KEY</code> in <code className="text-text">backend/.env</code> and
          restart the API to search and import any film. Until then, add movies by hand — the theme engine works the same.
        </p>
      </div>
    );
  }

  async function search(e: React.FormEvent) {
    e.preventDefault();
    if (q.trim().length < 2) return;
    setBusy("search");
    try {
      setHits(await api<TmdbHit[]>(`/admin/tmdb/search?q=${encodeURIComponent(q.trim())}`));
    } catch (err) {
      toast((err as ApiError).message, "error");
    } finally {
      setBusy(null);
    }
  }

  async function importOne(h: TmdbHit) {
    setBusy(h.tmdb_id);
    try {
      const m = await api<Movie>(`/admin/tmdb/import/${h.tmdb_id}`, { method: "POST" });
      const look = m.theme.archetypes.join(" + ") || "signature palette";
      toast(`${m.title} imported · ${look}`, "success");
      setHits((list) => list?.map((x) => (x.tmdb_id === h.tmdb_id ? { ...x, imported_id: m.id } : x)) ?? null);
      onImported(m);
    } catch (err) {
      toast((err as ApiError).message, "error");
    } finally {
      setBusy(null);
    }
  }

  return (
    <section className="glass rounded-2xl p-4">
      <form onSubmit={search} className="flex gap-2">
        <input className="input flex-1" placeholder="Import from TMDB — try “Pushpa”, “Interstellar”, “Kantara”…"
               value={q} onChange={(e) => setQ(e.target.value)} aria-label="Search TMDB" />
        <button className="btn btn-primary" disabled={busy === "search"}>{busy === "search" ? "Searching…" : "Search"}</button>
      </form>
      {hits && hits.length === 0 && <p className="text-sm text-muted mt-3">Nothing on TMDB for that.</p>}
      {hits && hits.length > 0 && (
        <ul className="mt-3 grid sm:grid-cols-2 gap-2">
          {hits.map((h) => (
            <li key={h.tmdb_id} className="flex gap-3 rounded-xl border border-line p-2">
              {h.poster_thumb ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={h.poster_thumb} alt="" className="w-12 h-18 object-cover rounded-md shrink-0" loading="lazy" />
              ) : <span className="w-12 h-18 rounded-md bg-white/5 shrink-0" />}
              <div className="min-w-0 flex-1">
                <p className="font-semibold text-sm truncate">{h.title} {h.year && <span className="text-muted font-normal">({h.year})</span>}</p>
                <p className="text-[11px] text-muted">{h.language}{h.rating ? ` · ★ ${h.rating}` : ""}</p>
                <p className="text-[11px] text-muted line-clamp-2 mt-0.5">{h.overview}</p>
              </div>
              <button className="btn btn-ghost self-center text-xs" disabled={!!h.imported_id || busy === h.tmdb_id}
                      onClick={() => importOne(h)}>
                {h.imported_id ? "Added" : busy === h.tmdb_id ? "…" : "Import"}
              </button>
            </li>
          ))}
        </ul>
      )}
      <p className="text-[10px] text-muted mt-3">This product uses the TMDB API but is not endorsed or certified by TMDB.</p>
    </section>
  );
}
