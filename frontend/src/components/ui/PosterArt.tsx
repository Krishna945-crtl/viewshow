import { assetUrl } from "@/lib/api";
import { hashString } from "@/lib/theme";
import type { Movie } from "@/lib/types";

/**
 * Original, generated key art - no copyrighted posters needed. Colours come from
 * the movie's theme, shapes from a hash of the title, so every film looks unique.
 * If an admin uploaded an authorised poster_url we show that instead.
 */
export default function PosterArt({ movie, className = "" }: { movie: Movie; className?: string }) {
  if (movie.poster_url) {
    // eslint-disable-next-line @next/next/no-img-element
    return <img src={assetUrl(movie.poster_url)!} alt={`${movie.title} poster`} className={`object-cover ${className}`} loading="lazy" />;
  }
  const { primary, secondary, accent, background } = movie.theme.palette;
  const h = hashString(movie.title);
  const r = (i: number) => ((h >> (i * 3)) & 255) / 255;
  const kind = movie.theme.particles.kind;
  const id = `p${h.toString(36)}`;
  const circles = Array.from({ length: 5 }, (_, i) => ({ cx: 20 + r(i) * 160, cy: 60 + r(i + 2) * 160, rr: 30 + r(i + 4) * 70 }));

  return (
    <svg viewBox="0 0 200 300" className={className} role="img" aria-label={`${movie.title} artwork`} preserveAspectRatio="xMidYMid slice">
      <defs>
        <linearGradient id={`${id}g`} x1="0" y1="0" x2="0.3" y2="1">
          <stop offset="0" stopColor={secondary} />
          <stop offset="0.55" stopColor={background} />
          <stop offset="1" stopColor={primary} stopOpacity="0.85" />
        </linearGradient>
        <radialGradient id={`${id}r`}>
          <stop offset="0" stopColor={accent} stopOpacity="0.9" />
          <stop offset="1" stopColor={accent} stopOpacity="0" />
        </radialGradient>
        <filter id={`${id}b`}><feGaussianBlur stdDeviation="9" /></filter>
      </defs>
      <rect width="200" height="300" fill={`url(#${id}g)`} />
      <g filter={`url(#${id}b)`} opacity="0.75">
        {circles.map((c, i) => (
          <circle key={i} cx={c.cx} cy={c.cy} r={c.rr} fill={i % 2 ? primary : `url(#${id}r)`} opacity={0.35 + r(i) * 0.4} />
        ))}
      </g>
      {kind === "sand" && <path d={`M0 ${215 + r(1) * 20} Q 60 ${185 + r(2) * 25} 120 ${215} T 200 ${205} V300 H0Z`} fill={primary} opacity="0.55" />}
      {kind === "bubbles" && Array.from({ length: 9 }, (_, i) => <circle key={i} cx={20 + r(i) * 160} cy={120 + r(i + 1) * 160} r={2 + r(i + 3) * 5} fill="none" stroke={accent} opacity="0.6" />)}
      {kind === "stars" && Array.from({ length: 24 }, (_, i) => <circle key={i} cx={r(i) * 200} cy={r(i + 5) * 150} r={0.6 + r(i + 2)} fill="#fff" opacity={0.4 + r(i) * 0.6} />)}
      {(kind === "rain") && Array.from({ length: 22 }, (_, i) => <line key={i} x1={r(i) * 200} y1={r(i + 3) * 300} x2={r(i) * 200 - 6} y2={r(i + 3) * 300 + 22} stroke={accent} opacity="0.35" />)}
      <rect y="190" width="200" height="110" fill={`url(#${id}g)`} opacity="0.6" />
      <text x="14" y="262" fill="#fff" fontSize={movie.title.length > 16 ? 15 : 19} fontWeight="800" style={{ letterSpacing: "0.02em" }}>
        {movie.title.toUpperCase().slice(0, 26)}
      </text>
      <text x="14" y="282" fill="#fff" fontSize="9" opacity="0.72" style={{ letterSpacing: "0.04em" }}>{movie.genres.slice(0, 2).join(" · ").toUpperCase()}</text>
    </svg>
  );
}
