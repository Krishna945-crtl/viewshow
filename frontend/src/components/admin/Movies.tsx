"use client";

import { useEffect, useRef, useState } from "react";
import MovieImport from "@/components/admin/MovieImport";
import PosterArt from "@/components/ui/PosterArt";
import ThemeExplain, { Swatches } from "@/components/ui/ThemeExplain";
import { Spinner } from "@/components/ui/bits";
import { toast } from "@/components/ui/toast";
import { api, ApiError } from "@/lib/api";
import type { Movie, Swatch, Theme } from "@/lib/types";
import { useApi } from "@/lib/useApi";

const csv = (s: string) => s.split(",").map((x) => x.trim()).filter(Boolean);
const EMPTY = { title: "", tagline: "", synopsis: "", genres: "", mood_tags: "", keywords: "", palette_hint: "", language: "English",
  certificate: "UA", runtime_minutes: 120, rating: "", trailer_url: "", poster_url: "", cast: "", theme_id: "", is_active: true };
type Form = typeof EMPTY & { id?: string; art_palette?: Swatch[] };

const lookOf = (m: Movie) => m.theme.source === "custom" ? `Theme: ${m.theme.name}` : `Auto: ${m.theme.archetypes.join(" + ") || "signature"}`;

export default function Movies() {
  const { data: movies, reload } = useApi<Movie[]>("/admin/movies");
  const { data: themes } = useApi<{ id: string; name: string }[]>("/admin/themes");
  const [edit, setEdit] = useState<Form | null>(null);
  const [preview, setPreview] = useState<Theme | null>(null);
  const editor = useRef<HTMLDivElement>(null);
  const editing = edit?.id ?? (edit ? "new" : null);
  useEffect(() => {
    if (editing) editor.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, [editing]);

  const open = (m?: Movie) => {
    setPreview(m?.theme ?? null);
    setEdit(m ? {
      id: m.id, title: m.title, tagline: m.tagline ?? "", synopsis: m.synopsis ?? "", genres: m.genres.join(", "),
      mood_tags: (m.mood_tags ?? []).join(", "), keywords: (m.keywords ?? []).join(", "), palette_hint: (m.palette_hint ?? []).join(", "),
      language: m.language, certificate: m.certificate, runtime_minutes: m.runtime_minutes, rating: m.rating?.toString() ?? "",
      trailer_url: m.trailer_url ?? "", poster_url: m.poster_url ?? "", cast: (m.cast ?? []).join(", "), theme_id: m.theme_id ?? "",
      is_active: m.is_active, art_palette: m.art_palette ?? [],
    } : { ...EMPTY });
  };

  const signals = (f: Form) => ({
    title: f.title || "Untitled", tagline: f.tagline || null, synopsis: f.synopsis, genres: csv(f.genres),
    mood_tags: csv(f.mood_tags), keywords: csv(f.keywords), palette_hint: csv(f.palette_hint), art_palette: f.art_palette ?? [],
  });

  async function previewTheme() {
    if (!edit) return;
    try {
      setPreview(await api<Theme>("/admin/themes/preview", { body: signals(edit) }));
    } catch (err) {
      toast((err as ApiError).message, "error");
    }
  }

  async function save(e: React.FormEvent) {
    e.preventDefault();
    if (!edit) return;
    const { id, art_palette: _art, ...rest } = edit; // eslint-disable-line @typescript-eslint/no-unused-vars
    const body = {
      ...rest, genres: csv(edit.genres), mood_tags: csv(edit.mood_tags), keywords: csv(edit.keywords), palette_hint: csv(edit.palette_hint),
      cast: csv(edit.cast), rating: edit.rating === "" ? null : Number(edit.rating), runtime_minutes: Number(edit.runtime_minutes),
      trailer_url: edit.trailer_url || null, poster_url: edit.poster_url || null, theme_id: edit.theme_id || null, tagline: edit.tagline || null,
    };
    try {
      const m = await api<Movie>(id ? `/admin/movies/${id}` : "/admin/movies", { method: id ? "PUT" : "POST", body });
      toast(`Saved · ${lookOf(m)}`, "success");
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
    <div className="space-y-4">
      <MovieImport onImported={(m) => { reload(); open(m); }} />
      <button className="btn btn-primary" onClick={() => open()}>+ Add a movie by hand</button>

      {edit && (
        <div ref={editor} className="grid lg:grid-cols-[1fr_300px] gap-4 scroll-mt-20">
          <form onSubmit={save} className="glass rounded-2xl p-4 grid sm:grid-cols-2 gap-3 text-sm">
            <label>Title<input required className="input mt-1" {...f("title")} /></label>
            <label>Tagline<input className="input mt-1" {...f("tagline")} /></label>
            <label className="sm:col-span-2">Synopsis<textarea className="input mt-1 min-h-20" {...f("synopsis")} /></label>
            <label>Genres (comma)<input className="input mt-1" placeholder="Action, Crime" {...f("genres")} /></label>
            <label>Keywords (comma)<input className="input mt-1" placeholder="smuggling, forest, revenge" {...f("keywords")} /></label>
            <label>Mood tags (strongest hint)<input className="input mt-1" placeholder="desert, storm, neon" {...f("mood_tags")} /></label>
            <label>Key-art colours (#hex, up to 3)<input className="input mt-1" placeholder="#1b3a6b, #7fd3ff" {...f("palette_hint")} /></label>
            <label>Theme<select className="input mt-1" {...f("theme_id")}><option value="">Auto-generate from metadata</option>{themes?.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}</select></label>
            <label>Language<input className="input mt-1" {...f("language")} /></label>
            <label>Certificate<input className="input mt-1" {...f("certificate")} /></label>
            <label>Runtime (min)<input type="number" min={1} className="input mt-1" {...f("runtime_minutes")} /></label>
            <label>Rating<input type="number" step="0.1" min={0} max={10} className="input mt-1" {...f("rating")} /></label>
            <label>Trailer URL (authorised)<input className="input mt-1" placeholder="https://youtube.com/..." {...f("trailer_url")} /></label>
            <label>Poster URL (authorised, optional)<input className="input mt-1" {...f("poster_url")} /></label>
            <label className="sm:col-span-2">Cast (comma)<input className="input mt-1" {...f("cast")} /></label>
            <div className="sm:col-span-2 flex flex-wrap gap-2">
              <button className="btn btn-primary">Save</button>
              <button type="button" className="btn btn-ghost" onClick={previewTheme}>Preview theme</button>
              <button type="button" className="btn btn-ghost" onClick={() => setEdit(null)}>Cancel</button>
            </div>
          </form>

          <aside className="space-y-4">
            {preview && (
              <section className="glass rounded-2xl p-4" aria-live="polite">
                <h3 className="font-semibold text-sm">Why this look?</h3>
                <div className="flex gap-1.5 my-3">
                  {[preview.palette.primary, preview.palette.secondary, preview.palette.accent].map((c) => (
                    <span key={c} className="size-7 rounded-lg border border-line" style={{ background: c }} title={c} />
                  ))}
                  <span className="text-[11px] text-muted self-center ml-1 capitalize">{preview.particles.kind}</span>
                </div>
                <ThemeExplain theme={preview} />
              </section>
            )}
            {edit.id && <Artwork movieId={edit.id} art={edit.art_palette ?? []} onChange={(m) => {
              setEdit({ ...edit, art_palette: m.art_palette ?? [], poster_url: m.poster_url ?? "" });
              setPreview(m.theme);
              reload();
            }} />}
          </aside>
        </div>
      )}

      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-4">
        {movies.map((m) => (
          <button key={m.id} className={`text-left ${m.is_active ? "" : "opacity-40"}`} onClick={() => open(m)}>
            <div className="aspect-[2/3] rounded-xl overflow-hidden border border-line"><PosterArt movie={m} className="w-full h-full" /></div>
            <p className="text-sm font-semibold mt-1 truncate">{m.title}</p>
            <p className="text-[11px] text-muted truncate capitalize">{lookOf(m)}</p>
          </button>
        ))}
      </div>
    </div>
  );
}

function Artwork({ movieId, art, onChange }: { movieId: string; art: Swatch[]; onChange: (m: Movie) => void }) {
  const [file, setFile] = useState<File | null>(null);
  const [keep, setKeep] = useState(false);
  const [busy, setBusy] = useState(false);

  async function upload() {
    if (!file) return;
    setBusy(true);
    const form = new FormData();
    form.append("file", file);
    form.append("keep_image", String(keep));
    try {
      onChange(await api<Movie>(`/admin/movies/${movieId}/artwork`, { method: "POST", body: form }));
      toast("Poster colours applied to the theme", "success");
      setFile(null);
    } catch (err) {
      toast((err as ApiError).message, "error");
    } finally {
      setBusy(false);
    }
  }

  async function clear() {
    onChange(await api<Movie>(`/admin/movies/${movieId}/artwork`, { method: "DELETE" }));
  }

  return (
    <section className="glass rounded-2xl p-4 text-sm space-y-3">
      <h3 className="font-semibold">Poster colours</h3>
      <p className="text-xs text-muted">Upload the key art. Only its colours are kept unless you confirm you&apos;re licensed to show it.</p>
      {art.length > 0 && <Swatches colours={art} />}
      <input type="file" accept="image/jpeg,image/png,image/webp" className="block w-full text-xs file:btn file:btn-ghost file:mr-2"
             onChange={(e) => setFile(e.target.files?.[0] ?? null)} aria-label="Poster image" />
      <label className="flex items-start gap-2 text-xs">
        <input type="checkbox" checked={keep} onChange={(e) => setKeep(e.target.checked)} className="mt-0.5" />
        <span>I have the rights to display this image as the poster</span>
      </label>
      <div className="flex gap-2">
        <button type="button" className="btn btn-primary text-xs" disabled={!file || busy} onClick={upload}>{busy ? "Reading colours…" : "Upload"}</button>
        {art.length > 0 && <button type="button" className="btn btn-ghost text-xs" onClick={clear}>Remove</button>}
      </div>
    </section>
  );
}
