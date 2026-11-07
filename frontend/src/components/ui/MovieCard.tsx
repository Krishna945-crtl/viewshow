import Link from "next/link";
import type { Movie } from "@/lib/types";
import PosterArt from "./PosterArt";

export default function MovieCard({ movie, onHover }: { movie: Movie; onHover?: (m: Movie) => void }) {
  return (
    <Link href={`/movie/?id=${movie.slug}`} className="group block" onMouseEnter={() => onHover?.(movie)} onFocus={() => onHover?.(movie)}>
      <div className="relative aspect-[2/3] rounded-2xl overflow-hidden border border-line transition-transform duration-300 group-hover:-translate-y-1 group-hover:shadow-[0_20px_50px_-20px_var(--cv-primary)]">
        <PosterArt movie={movie} className="absolute inset-0 w-full h-full" />
        <div className="absolute top-2 left-2 flex gap-1">
          <span className="chip !py-0.5 !px-2 !text-[10px] bg-black/50">{movie.certificate}</span>
          {movie.rating && <span className="chip !py-0.5 !px-2 !text-[10px] bg-black/50">★ {movie.rating.toFixed(1)}</span>}
        </div>
        <span className="absolute bottom-2 right-2 size-3 rounded-full border border-white/40" style={{ background: movie.theme.palette.primary }}
              title={`Theme: ${movie.theme.mood || movie.theme.name}`} />
      </div>
      <div className="mt-2 px-0.5">
        <p className="font-semibold leading-tight truncate">{movie.title}</p>
        <p className="text-xs text-muted truncate">{movie.language} · {movie.genres.slice(0, 2).join(", ") || "—"}</p>
      </div>
    </Link>
  );
}
