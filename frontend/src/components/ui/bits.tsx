export function Spinner({ label = "Loading" }: { label?: string }) {
  return (
    <div className="flex items-center justify-center gap-3 py-16 text-muted" role="status">
      <span className="size-5 rounded-full border-2 border-line border-t-accent animate-spin" aria-hidden />
      {label}…
    </div>
  );
}

export function Empty({ title, hint, children }: { title: string; hint?: string; children?: React.ReactNode }) {
  return (
    <div className="text-center py-16 px-6">
      <p className="text-lg font-semibold">{title}</p>
      {hint && <p className="text-muted mt-1 text-sm">{hint}</p>}
      {children && <div className="mt-5">{children}</div>}
    </div>
  );
}

export function DemoBadge() {
  return (
    <span className="text-[10px] uppercase tracking-wider rounded-full px-2 py-0.5 border border-amber-400/40 text-amber-300"
          title="Sample venue with simulated seat inventory - not a real cinema">
      Demo venue
    </span>
  );
}

export function Stat({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="glass rounded-2xl p-4">
      <div className="text-xs text-muted">{label}</div>
      <div className="text-2xl font-bold mt-1">{value}</div>
    </div>
  );
}
