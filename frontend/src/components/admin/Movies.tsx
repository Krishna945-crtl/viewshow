"use client";

import { useState } from "react";
import PosterArt from "@/components/ui/PosterArt";
import { Spinner } from "@/components/ui/bits";
import { toast } from "@/components/ui/toast";
import { api, ApiError } from "@/lib/api";
import type { Movie } from "@/lib/types";
import { useApi } from "@/lib/useApi";

const csv = (s: string) => s.split(",").map((x) => x.trim()).filter(Boolean);
const EMPTY = { title: "", tagline: "", synopsis: "", genres: "", mood_tags: "", palette_hint: "", language: "English", certificate: "UA",
  runtime_minutes: 120, rating: "", trailer_url: "", poster_url: "", cast: "", theme_id: "", is_active: true };

export default function Movies() {
  const { data: movies, reload } = useApi<Movie[]>("/admin/movies");
  const { data: themes } = useApi<{ id: string; name: string }[]>("/admin/themes");
  const [edit, setEdit] = useState<(typeof EMPTY & { id?: string }) | null>(null);

  const open = (m?: Movie) => setEdit(m ? {
    id: m.id, title: m.title, tagline: m.tagline ?? "", synopsis: m.synopsis ?? "", genres: m.genres.join(", "),
    mood_tags: (m.mood_tags ?? []).join(", "), palette_hint: (m.palette_hint ?? []).join(", "), language: m.language,
    certificate: m.certificate, runtime_minutes: m.runtime_minutes, rating: m.rating?.toString() ?? "",
    trailer_url: m.trailer_url ?? "", poster_url: m.poster_url ?? "", cast: (m.cast ?? []).join(", "), theme_id: m.theme_id ?? "", is_active: m.is_active,
  } : { ...EMPTY });

  async function save(e: React.FormEvent) {
    e.preventDefault();
    if (!edit) return;
    const body = {
      ...edit, genres: csv(edit.genres), mood_tags: csv(edit.mood_tags), palette_hint: csv(edit.palette_hint), cast: csv(edit.cast),
      rating: edit.rating === "" ? null : Number(edit.rating), runtime_minutes: Number(edit.runtime_minutes),
      trailer_url: edit.trailer_url || null, poster_url: edit.poster_url || null, theme_id: edit.theme_id || null, tagline: edit.tagline || null,
    };
    delete (body as { id?: string }).id;
    try {
      const m = await api<Movie>(edit.id ? `/admin/movies/${edit.id}` : "/admin/movies", { method: edit.id ? "PUT" : "POST", body });
      toast(`Saved · theme: ${m.theme.source === "auto" ? "auto (" + (m.theme.archetypes.join("+") || "title palette") + ")" : m.theme.name}`, "success");
      setEdit(null);
      reload();
    } catch (err) {
      toast((err as ApiError).message, "error");
    }
  }

  if (!movies) return <Spinner />;
  const f = (k: keyof typeof EMPTY) => ({
    value: String(edit?.[k] ?? ""),
    onChange: (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => setEdit({ ...edit!, [k]: e.target.value }),
  });

  return (
    <div>
      <button className="btn btn-primary" onClick={() => open()}>+ New movie</button>
      {edit && (
        <form onSubmit={save} className="glass rounded-2xl p-4 mt-4 grid sm:grid-cols-2 gap-3 text-sm">
          <label>Title<input required className="input mt-1" {...f("title")} /></label>
          <label>Tagline<input className="input mt-1" {...f("tagline")} /></label>
          <label className="sm:col-span-2">Synopsis<textarea className="input mt-1 min-h-20" {...f("synopsis")} /></label>
          <label>Genres (comma)<input className="input mt-1" {...f("genres")} /></label>
          <label>Mood tags (feed the theme engine)<input className="input mt-1" placeholder="desert, storm, neon" {...f("mood_tags")} /></label>
          <label>Key-art colours (#hex, up to 3)<input className="input mt-1" placeholder="#1b3a6b, #7fd3ff" {...f("palette_hint")} /></label>
          <label>Theme<select className="input mt-1" {...f("theme_id")}><option value="">Auto-generate from metadata</option>{themes?.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}</select></label>
          <label>Language<input className="input mt-1" {...f("language")} /></label>
          <label>Certificate<input className="input mt-1" {...f("certificate")} /></label>
          <label>Runtime (min)<input type="number" min={1} className="input mt-1" {...f("runtime_minutes")} /></label>
          <label>Rating<input type="number" step="0.1" min={0} max={10} className="input mt-1" {...f("rating")} /></label>
          <label>Trailer URL (authorised)<input className="input mt-1" placeholder="https://youtube.com/..." {...f("trailer_url")} /></label>
          <label>Poster URL (authorised, optional)<input className="input mt-1" {...f("poster_url")} /></label>
          <label className="sm:col-span-2">Cast (comma)<input className="input mt-1" {...f("cast")} /></label>
          <div className="sm:col-span-2 flex gap-2"><button className="btn btn-primary">Save</button><button type="button" className="btn btn-ghost" onClick={() => setEdit(null)}>Cancel</button></div>
        </form>
      )}
      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-4 mt-4">
        {movies.map((m) => (
          <button key={m.id} className={`text-left ${m.is_active ? "" : "opacity-40"}`} onClick={() => open(m)}>
            <div className="aspect-[2/3] rounded-xl overflow-hidden border border-line"><PosterArt movie={m} className="w-full h-full" /></div>
            <p className="text-sm font-semibold mt-1 truncate">{m.title}</p>
            <p className="text-[11px] text-muted truncate">{m.theme.source === "custom" ? `Theme: ${m.theme.name}` : `Auto: ${m.theme.archetypes.join("+") || "title palette"}`}</p>
          </button>
        ))}
      </div>
    </div>
  );
}
