"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import PosterArt from "@/components/ui/PosterArt";
import ThemeApplier from "@/components/ui/ThemeApplier";
import { Empty, Spinner } from "@/components/ui/bits";
import { runtime } from "@/lib/format";
import type { Movie } from "@/lib/types";
import { useApi } from "@/lib/useApi";

function youtubeEmbed(url: string) {
  const m = url.match(/(?:youtu\.be\/|v=|embed\/)([\w-]{11})/);
  return m ? `https://www.youtube-nocookie.com/embed/${m[1]}` : null;
}

export default function MovieDetail() {
  const id = useSearchParams().get("id");
  const { data: m, loading, error } = useApi<Movie>(id ? `/movies/${id}` : null);
  if (loading) return <Spinner />;
  if (error || !m) return <Empty title="Movie not found" hint={error?.message} />;
  const trailer = m.trailer_url ? youtubeEmbed(m.trailer_url) : null;
  const t = m.theme;

  return (
    <div className="mx-auto max-w-5xl px-4 py-6">
      <ThemeApplier theme={t} />
      <div className="grid sm:grid-cols-[240px_1fr] gap-6 sm:gap-10">
        <div className="aspect-[2/3] rounded-3xl overflow-hidden border border-line max-w-60 sm:max-w-none shadow-[0_30px_80px_-30px_var(--cv-primary)]">
          <PosterArt movie={m} className="w-full h-full" />
        </div>
        <div>
          <h1 className="text-3xl sm:text-4xl font-bold">{m.title}</h1>
          {m.tagline && <p className="text-muted mt-1">{m.tagline}</p>}
          <div className="flex flex-wrap gap-2 mt-4 text-xs">
            <span className="chip">{m.certificate}</span>
            <span className="chip">{runtime(m.runtime_minutes)}</span>
            <span className="chip">{m.language}</span>
            {m.rating && <span className="chip">★ {m.rating.toFixed(1)}</span>}
            {m.genres.map((g) => <span key={g} className="chip">{g}</span>)}
          </div>
          <p className="mt-5 leading-relaxed text-text/90">{m.synopsis}</p>
          {!!m.cast?.length && <p className="text-sm text-muted mt-3">Cast: {m.cast.join(", ")}</p>}
          <div className="mt-6 flex gap-3">
            <Link href={`/showtimes/?movie=${m.slug}`} className="btn btn-primary">Book tickets</Link>
            <Link href={`/lab/?movie=${m.slug}`} className="btn btn-ghost">Preview the hall</Link>
          </div>

          <div className="mt-8 glass rounded-2xl p-4">
            <div className="flex items-center justify-between">
              <h2 className="font-semibold">Auditorium atmosphere</h2>
              <span className="text-[11px] text-muted">{t.source === "custom" ? "Curated theme" : `Auto-generated · ${t.archetypes.join(" + ") || "title palette"}`}</span>
            </div>
            <p className="text-sm text-muted mt-1 capitalize">{t.mood}</p>
            <div className="flex gap-2 mt-3" aria-label="Theme colours">
              {[t.palette.primary, t.palette.secondary, t.palette.accent, t.lighting.wall_wash, t.fog.color].map((c, i) => (
                <span key={i} className="size-8 rounded-lg border border-line" style={{ background: c }} title={c} />
              ))}
            </div>
            <p className="text-xs text-muted mt-3">Particles: {t.particles.kind} · Ambience: {t.sound.preset.replace("_", " ")} (off until you enable it)</p>
          </div>
        </div>
      </div>

      <section className="mt-10">
        <h2 className="text-xl font-semibold mb-3">Trailer</h2>
        {trailer ? (
          <div className="aspect-video rounded-2xl overflow-hidden border border-line">
            <iframe src={trailer} title={`${m.title} trailer`} className="w-full h-full" allow="encrypted-media; picture-in-picture" allowFullScreen loading="lazy" />
          </div>
        ) : (
          <p className="text-sm text-muted glass rounded-2xl p-6">No trailer has been added for this title yet. Admins can attach an authorised trailer link.</p>
        )}
      </section>
    </div>
  );
}
