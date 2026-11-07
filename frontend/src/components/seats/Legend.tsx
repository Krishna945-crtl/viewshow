export default function Legend({ prices }: { prices: Record<string, number> }) {
  const items = [
    { cls: "bg-seat-available", label: "Available" },
    { cls: "bg-seat-selected", label: "Your pick", mark: "✓" },
    { cls: "bg-seat-held seat-held-pattern", label: "Held" },
    { cls: "bg-seat-booked text-gray-300", label: "Booked", mark: "✕" },
  ];
  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-xs text-muted" aria-label="Seat legend">
      {items.map((i) => (
        <span key={i.label} className="flex items-center gap-1.5">
          <span className={`size-4 rounded grid place-items-center text-[9px] text-black ${i.cls}`} aria-hidden>{i.mark}</span>
          {i.label}
        </span>
      ))}
      <span className="hidden sm:inline text-line">|</span>
      {Object.entries(prices).map(([k, v]) => (
        <span key={k} className="capitalize">{k} ₹{Math.round(v / 100)}</span>
      ))}
    </div>
  );
}
