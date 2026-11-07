"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import { useCam } from "@/components/theatre/camera";
import SoundControl from "@/components/ui/SoundControl";
import ThemeApplier from "@/components/ui/ThemeApplier";
import { Spinner } from "@/components/ui/bits";
import { api } from "@/lib/api";
import { useDemoMap } from "@/lib/demoMap";
import type { Movie, Theme } from "@/lib/types";
import { useApi } from "@/lib/useApi";
import { detectGpu } from "@/lib/webgl";

const Auditorium3D = dynamic(() => import("@/components/theatre/Auditorium3D"), { ssr: false });

/**
 * Same hall, different films. Switching movie only retargets the theme, so you
 * watch the auditorium crossfade instead of reloading a new scene.
 */
export default function ThemeLab() {
  const initial = useSearchParams().get("movie");
  const { data: movies } = useApi<Movie[]>("/movies");
  const map = useDemoMap();
  const [theme, setTheme] = useState<Theme | null>(null);
  const [active, setActive] = useState<string | null>(initial);
  const [custom, setCustom] = useState({ title: "", genres: "", mood_tags: "", synopsis: "" });
  const [gpu, setGpu] = useState<string | null>(null);
  const go = useCam((c) => c.go);

  useEffect(() => setGpu(detectGpu()), []);

  useEffect(() => {
    if (!movies?.length) return;
    const m = movies.find((x) => x.slug === active) ?? movies[0];
    setTheme(m.theme);
    if (!active) setActive(m.slug);
  }, [movies, active]);

  async function tryCustom(e: React.FormEvent) {
    e.preventDefault();
    const split = (s: string) => s.split(",").map((x) => x.trim()).filter(Boolean);
    const t = await api<Theme>("/themes/preview", {
      body: { title: custom.title || "Untitled", genres: split(custom.genres), mood_tags: split(custom.mood_tags), synopsis: custom.synopsis },
    });
    setActive(null);
    setTheme(t);
  }

  return (
    <div className="mx-auto max-w-6xl px-4 py-6">
      <ThemeApplier theme={theme} />
      <h1 className="text-2xl sm:text-3xl font-bold">Theme Lab</h1>
      <p className="text-muted text-sm mt-1">One auditorium, every movie. Pick a film and watch the hall re-light itself — or describe any movie and let the engine design its atmosphere.</p>

      <div className="mt-4 flex gap-2 overflow-x-auto no-scrollbar pb-1">
        {(movies ?? []).map((m) => (
          <button key={m.id} className="chip flex items-center gap-1.5" aria-pressed={active === m.slug} onClick={() => setActive(m.slug)}>
            <span className="size-2.5 rounded-full" style={{ background: m.theme.palette.primary }} />{m.title}
          </button>
        ))}
      </div>

      <div className="mt-4 grid lg:grid-cols-[1fr_320px] gap-4">
        <div className="relative rounded-3xl overflow-hidden border border-line h-[52vh] min-h-80">
          {gpu === "none" ? (
            <p className="p-6 text-sm text-muted">WebGL isn&apos;t available on this device, so the 3D preview is off. The theme details still update on the right.</p>
          ) : map && theme ? (
            <>
              <Auditorium3D map={map} theme={theme} interactive={false} className="absolute inset-0" />
              <div className="absolute top-3 left-3 flex gap-1.5">
                {(["overview", "back", "side", "stage"] as const).map((v) => (
                  <button key={v} className="chip glass capitalize" onClick={() => go(v)}>{v}</button>
                ))}
              </div>
            </>
          ) : <Spinner label="Building the hall" />}
        </div>

        <aside className="space-y-4">
          {theme && (
            <section className="glass rounded-2xl p-4">
              <div className="flex items-center justify-between">
                <h2 className="font-semibold truncate">{theme.name}</h2>
                <SoundControl preset={theme.sound.preset} />
              </div>
              <p className="text-xs text-muted mt-1 capitalize">
                {theme.source === "custom" ? "Curated by admin" : `Auto · ${theme.archetypes.join(" + ") || "title-derived palette"}`} · {theme.mood}
              </p>
              <div className="grid grid-cols-5 gap-2 mt-3">
                {Object.entries(theme.palette).map(([k, c]) => (
                  <div key={k} className="text-center">
                    <span className="block aspect-square rounded-lg border border-line" style={{ background: c }} />
                    <span className="text-[9px] text-muted">{k}</span>
                  </div>
                ))}
              </div>
              <dl className="text-xs grid grid-cols-2 gap-1 mt-3">
                <dt className="text-muted">Particles</dt><dd>{theme.particles.kind}</dd>
                <dt className="text-muted">Fog density</dt><dd>{theme.fog.density.toFixed(3)}</dd>
                <dt className="text-muted">Light pulse</dt><dd>{theme.animation.light_pulse.toFixed(2)}</dd>
                <dt className="text-muted">Ambience</dt><dd>{theme.sound.preset.replace("_", " ")}</dd>
              </dl>
              {active && <Link href={`/showtimes/?movie=${active}`} className="btn btn-primary w-full mt-4">Book this movie</Link>}
            </section>
          )}
          <form onSubmit={tryCustom} className="glass rounded-2xl p-4 space-y-2">
            <h2 className="font-semibold">Theme any movie</h2>
            <input className="input" placeholder="Title" value={custom.title} onChange={(e) => setCustom({ ...custom, title: e.target.value })} />
            <input className="input" placeholder="Genres (comma separated)" value={custom.genres} onChange={(e) => setCustom({ ...custom, genres: e.target.value })} />
            <input className="input" placeholder="Mood tags e.g. jungle, rain" value={custom.mood_tags} onChange={(e) => setCustom({ ...custom, mood_tags: e.target.value })} />
            <textarea className="input min-h-20" placeholder="One-line synopsis" value={custom.synopsis} onChange={(e) => setCustom({ ...custom, synopsis: e.target.value })} />
            <button className="btn btn-primary w-full">Generate atmosphere</button>
          </form>
        </aside>
      </div>
    </div>
  );
}
