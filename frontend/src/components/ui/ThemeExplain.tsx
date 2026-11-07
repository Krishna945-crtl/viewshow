import type { Swatch, Theme } from "@/lib/types";

const FROM: Record<string, string> = {
  "poster colours": "Colours taken from the poster",
  "admin colours": "Colours picked by an admin",
  archetypes: "Colours from the matched atmospheres",
  "title signature": "No clues yet — a signature palette from the title",
};

/** "Why does this hall look like this?" — the engine's own reasoning, readable. */
export default function ThemeExplain({ theme, compact = false }: { theme: Theme; compact?: boolean }) {
  const e = theme.explain;
  if (theme.source === "custom") {
    return <p className="text-xs text-muted">Hand-tuned by an admin for this film.</p>;
  }
  if (!e) return null;
  const top = e.signals[0]?.score || 1;
  const signals = compact ? e.signals.slice(0, 2) : e.signals;

  return (
    <div className="text-xs space-y-2.5">
      <div className="flex items-center gap-2">
        <span className="text-muted">Confidence</span>
        <span className="flex-1 h-1.5 rounded-full bg-white/10 overflow-hidden" aria-hidden>
          <span className="block h-full rounded-full bg-[var(--cv-accent)]" style={{ width: `${Math.round(e.confidence * 100)}%` }} />
        </span>
        <span className="tabular-nums">{Math.round(e.confidence * 100)}%</span>
      </div>
      {signals.length > 0 && (
        <ul className="space-y-2">
          {signals.map((s) => (
            <li key={s.archetype}>
              <div className="flex items-center gap-2">
                <span className="font-semibold w-24 shrink-0">{s.label}</span>
                <span className="flex-1 h-1 rounded-full bg-white/10 overflow-hidden" aria-hidden>
                  <span className="block h-full bg-[var(--cv-primary)]" style={{ width: `${(s.score / top) * 100}%` }} />
                </span>
                <span className="tabular-nums text-muted w-8 text-right">{s.score.toFixed(1)}</span>
              </div>
              {!compact && s.evidence.length > 0 && (
                <p className="text-muted mt-0.5 pl-0.5 leading-relaxed">{s.evidence.join(" · ")}</p>
              )}
            </li>
          ))}
        </ul>
      )}
      <p className="text-muted">{FROM[e.palette_from] ?? e.palette_from}</p>
    </div>
  );
}

export function Swatches({ colours, size = "size-6" }: { colours: Swatch[]; size?: string }) {
  return (
    <div className="flex gap-1.5" aria-label="Extracted colours">
      {colours.map((c) => (
        <span key={c.hex} className={`${size} rounded-md border border-line`} style={{ background: c.hex }}
              title={`${c.hex} · ${Math.round(c.weight * 100)}% of the image`} />
      ))}
    </div>
  );
}
