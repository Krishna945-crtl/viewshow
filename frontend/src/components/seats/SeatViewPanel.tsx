"use client";

import { motion } from "framer-motion";
import { cap, rupees } from "@/lib/format";
import { displayState, useSeats } from "@/lib/seats";
import type { Seat } from "@/lib/types";

function Ring({ score }: { score: number }) {
  const c = 2 * Math.PI * 18;
  const color = score >= 80 ? "#22c55e" : score >= 60 ? "#eab308" : "#f97316";
  return (
    <svg viewBox="0 0 44 44" className="size-14 shrink-0" aria-hidden>
      <circle cx="22" cy="22" r="18" fill="none" stroke="rgba(255,255,255,.12)" strokeWidth="4" />
      <circle cx="22" cy="22" r="18" fill="none" stroke={color} strokeWidth="4" strokeDasharray={c}
              strokeDashoffset={c * (1 - score / 100)} strokeLinecap="round" transform="rotate(-90 22 22)" />
      <text x="22" y="26" textAnchor="middle" fontSize="12" fontWeight="700" fill="#fff">{score}</text>
    </svg>
  );
}

interface Props {
  seat: Seat;
  verified: boolean;
  inSeatView: boolean;
  onView: () => void;
  onExit: () => void;
  onToggle: () => void;
  onStep: (dir: -1 | 1) => void;
  onClose: () => void;
}

export default function SeatViewPanel({ seat, verified, inSeatView, onView, onExit, onToggle, onStep, onClose }: Props) {
  useSeats((s) => s.version);
  const d = displayState(useSeats.getState(), seat.id);
  const v = seat.view;
  const canToggle = d === "available" || d === "selected";
  return (
    <motion.section initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}
      className="glass rounded-2xl p-4 w-full sm:w-80 shadow-2xl" aria-label={`Seat ${seat.label} details`}>
      <div className="flex items-start gap-3">
        <Ring score={v.score} />
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <h3 className="font-bold text-lg">{seat.label}</h3>
            <span className="text-xs text-muted">{cap(seat.category)} · {rupees(seat.price_paise)}</span>
          </div>
          <p className="text-sm">{v.verdict}</p>
        </div>
        <button onClick={onClose} className="text-muted hover:text-text text-lg leading-none" aria-label="Close seat details">×</button>
      </div>
      <dl className="grid grid-cols-2 gap-x-3 gap-y-1.5 text-xs mt-3">
        <dt className="text-muted">Distance to screen</dt><dd className="text-right">{v.distance} m</dd>
        <dt className="text-muted">Screen fills</dt><dd className="text-right">{v.fov}° of view</dd>
        <dt className="text-muted">Off-centre angle</dt><dd className="text-right">{v.off_axis}°</dd>
        <dt className="text-muted">Head tilt</dt><dd className="text-right">{v.vertical > 0 ? "↑" : "↓"} {Math.abs(v.vertical)}°</dd>
      </dl>
      {!verified && (
        <p className="text-[11px] mt-2 text-amber-300/90">Visual estimate — this auditorium&apos;s dimensions haven&apos;t been verified by the venue.</p>
      )}
      <div className="flex gap-2 mt-3">
        <button className="btn btn-ghost !px-3" onClick={() => onStep(-1)} aria-label="Previous seat in row">‹</button>
        {inSeatView ? (
          <button className="btn btn-ghost flex-1" onClick={onExit}>Exit seat view</button>
        ) : (
          <button className="btn btn-ghost flex-1" onClick={onView}>👁 View from seat</button>
        )}
        <button className="btn btn-ghost !px-3" onClick={() => onStep(1)} aria-label="Next seat in row">›</button>
      </div>
      <button className={`btn w-full mt-2 ${d === "selected" ? "btn-ghost" : "btn-primary"}`} disabled={!canToggle} onClick={onToggle}>
        {d === "selected" ? "Remove seat" : d === "available" ? "Select this seat" : d === "booked" ? "Already booked" : d === "held" ? "Someone is holding it" : "Not available"}
      </button>
    </motion.section>
  );
}
