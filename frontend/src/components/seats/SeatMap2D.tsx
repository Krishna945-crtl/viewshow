"use client";

import { useMemo, useRef } from "react";
import { cap, rupees } from "@/lib/format";
import { displayState, useSeats, type DisplayState } from "@/lib/seats";
import type { Seat } from "@/lib/types";

const STYLE: Record<DisplayState, string> = {
  available: "bg-seat-available text-black hover:ring-2 hover:ring-accent",
  selected: "bg-seat-selected text-black ring-2 ring-white",
  pending: "bg-green-300 text-black animate-pulse",
  held: "bg-seat-held text-black seat-held-pattern cursor-not-allowed",
  booked: "bg-seat-booked text-gray-300 cursor-not-allowed",
  blocked: "bg-transparent border border-dashed border-gray-600 text-gray-600 cursor-not-allowed",
};
const CAT_SHAPE: Record<string, string> = { standard: "rounded-t-md", premium: "rounded-t-lg", vip: "rounded-t-xl", recliner: "rounded-xl" };
const STATE_TEXT: Record<DisplayState, string> = {
  available: "available", selected: "selected by you", pending: "updating", held: "held by someone else",
  booked: "booked", blocked: "not available",
};

/** Accessible flat seat map. Arrow keys move between seats, Enter/Space toggles. */
export default function SeatMap2D({ seats, onSeatClick }: { seats: Seat[]; onSeatClick: (s: Seat) => void }) {
  useSeats((s) => s.version);
  useSeats((s) => s.pending);
  const focused = useSeats((s) => s.focused);
  const st = useSeats.getState();
  const gridRef = useRef<HTMLDivElement>(null);

  const { rows, cols, byPos, rowLabels } = useMemo(() => {
    const rows = Math.max(...seats.map((s) => s.grid_row)) + 1;
    const cols = Math.max(...seats.map((s) => s.col)) + 1;
    const byPos = new Map<string, Seat>();
    const rowLabels: string[] = [];
    seats.forEach((s) => {
      byPos.set(`${s.grid_row}:${s.col}`, s);
      rowLabels[s.grid_row] = s.row;
    });
    return { rows, cols, byPos, rowLabels };
  }, [seats]);

  const move = (s: Seat, dr: number, dc: number) => {
    // walk in the direction until we hit a seat (skips aisles)
    for (let step = 1; step < 40; step++) {
      const r = s.grid_row + dr * step;
      if (dr && (r < 0 || r >= rows)) return;
      if (dr) {
        // nearest seat in that row by column
        let best: Seat | undefined;
        for (const cand of seats) if (cand.grid_row === r && (!best || Math.abs(cand.col - s.col) < Math.abs(best.col - s.col))) best = cand;
        if (best) return focusSeat(best);
        continue;
      }
      const c = s.col + dc * step;
      if (c < 0 || c >= cols) return;
      const hit = byPos.get(`${s.grid_row}:${c}`);
      if (hit) return focusSeat(hit);
    }
  };
  const focusSeat = (s: Seat) => {
    useSeats.getState().focus(s.id);
    gridRef.current?.querySelector<HTMLButtonElement>(`[data-seat="${s.id}"]`)?.focus();
  };
  const onKey = (e: React.KeyboardEvent, s: Seat) => {
    const map: Record<string, [number, number]> = { ArrowUp: [-1, 0], ArrowDown: [1, 0], ArrowLeft: [0, -1], ArrowRight: [0, 1] };
    if (map[e.key]) {
      e.preventDefault();
      move(s, ...map[e.key]);
    }
  };
  const tabSeat = focused ?? seats.find((s) => displayState(st, s.id) === "available")?.id ?? seats[0]?.id;
  const cell = "clamp(18px, calc((100vw - 64px) / " + (cols + 2) + "), 30px)";

  return (
    <div className="w-full overflow-auto no-scrollbar py-4" >
      <div className="mx-auto w-max">
        <div className="mx-auto mb-6 h-2 rounded-full bg-gradient-to-r from-transparent via-accent to-transparent shadow-[0_0_30px_var(--cv-accent)]"
             style={{ width: `calc(${cell} * ${cols} * 0.8)` }} />
        <p className="text-center text-[10px] tracking-[0.4em] text-muted -mt-4 mb-4">SCREEN</p>
        <div ref={gridRef} role="grid" aria-label="Seat map. Use arrow keys to move between seats and Enter to select."
             className="grid gap-[3px]" style={{ gridTemplateColumns: `auto repeat(${cols}, ${cell}) auto` }}>
          {Array.from({ length: rows }).map((_, r) => (
            <div role="row" key={r} className="contents">
              <span className="text-[10px] text-muted self-center pr-1.5 text-right" aria-hidden>{rowLabels[r]}</span>
              {Array.from({ length: cols }).map((__, c) => {
                const s = byPos.get(`${r}:${c}`);
                if (!s) return <span key={c} aria-hidden />;
                const d = displayState(st, s.id);
                const clickable = d === "available" || d === "selected";
                return (
                  <button
                    key={c}
                    role="gridcell"
                    data-seat={s.id}
                    tabIndex={s.id === tabSeat ? 0 : -1}
                    aria-label={`${s.label}, ${cap(s.category)}, ${rupees(s.price_paise)}, ${STATE_TEXT[d]}${s.accessible ? ", wheelchair accessible" : ""}, view score ${s.view.score}`}
                    aria-selected={d === "selected"}
                    aria-disabled={!clickable}
                    onClick={() => clickable && onSeatClick(s)}
                    onFocus={() => useSeats.getState().focus(s.id)}
                    onMouseEnter={() => useSeats.getState().hover(s.id)}
                    onMouseLeave={() => useSeats.getState().hover(null)}
                    onKeyDown={(e) => onKey(e, s)}
                    className={`seat-btn relative grid place-items-center text-[9px] font-semibold transition ${CAT_SHAPE[s.category]} ${STYLE[d]} ${focused === s.id ? "outline outline-2 outline-accent" : ""}`}
                    style={{ width: cell, height: cell }}
                  >
                    {d === "booked" ? "✕" : d === "selected" ? "✓" : s.accessible && d === "available" ? "♿" : s.number}
                  </button>
                );
              })}
              <span className="text-[10px] text-muted self-center pl-1.5" aria-hidden>{rowLabels[r]}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
