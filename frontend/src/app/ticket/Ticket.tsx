"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { QRCodeSVG } from "qrcode.react";
import ThemeApplier from "@/components/ui/ThemeApplier";
import { Empty, Spinner } from "@/components/ui/bits";
import { rupees, showDate, showTime } from "@/lib/format";
import type { Booking, Movie } from "@/lib/types";
import { useApi } from "@/lib/useApi";

export default function Ticket() {
  const id = useSearchParams().get("booking");
  const { data: b, loading, error } = useApi<Booking>(id ? `/bookings/${id}` : null);
  const { data: movie } = useApi<Movie>(b ? `/movies/${b.movie.id}` : null);
  if (loading) return <Spinner />;
  if (error || !b) return <Empty title="Ticket not found" hint={error?.message} />;
  if (b.status !== "CONFIRMED") return <Empty title={`Booking ${b.status.toLowerCase()}`} hint="No ticket for this booking." />;

  return (
    <div className="mx-auto max-w-sm px-4 py-6">
      <ThemeApplier theme={movie?.theme} />
      <article className="rounded-[28px] overflow-hidden border border-line shadow-[0_40px_100px_-40px_var(--cv-primary)]" aria-label="Digital ticket">
        <div className="p-6 bg-gradient-to-br from-primary/40 via-secondary to-bg">
          <p className="text-[10px] uppercase tracking-[0.3em] text-accent">CineVerse 3D · Ticket</p>
          <h1 className="text-2xl font-bold mt-2">{b.movie.title}</h1>
          <p className="text-sm text-muted">{b.movie.certificate} · {b.show.format} · {b.show.language}</p>
          <div className="grid grid-cols-2 gap-3 mt-5 text-sm">
            <div><div className="text-[10px] uppercase text-muted">Date</div>{showDate(b.show.starts_at)}</div>
            <div><div className="text-[10px] uppercase text-muted">Time</div>{showTime(b.show.starts_at)}</div>
            <div className="col-span-2"><div className="text-[10px] uppercase text-muted">Venue</div>{b.theatre.name} · {b.show.auditorium}</div>
            <div className="col-span-2"><div className="text-[10px] uppercase text-muted">Seats</div><span className="text-lg font-bold">{b.seats.map((s) => s.label).join(", ")}</span></div>
          </div>
        </div>
        <div className="relative h-0 border-t-2 border-dashed border-line">
          <span className="absolute -left-3 -top-3 size-6 rounded-full bg-bg" />
          <span className="absolute -right-3 -top-3 size-6 rounded-full bg-bg" />
        </div>
        <div className="p-6 bg-surface flex flex-col items-center">
          <div className="bg-white p-3 rounded-2xl">
            <QRCodeSVG value={b.ticket_payload!} size={180} level="M" title={`Ticket QR for booking ${b.reference}`} />
          </div>
          <p className="mt-3 font-mono tracking-widest text-lg">{b.reference}</p>
          <p className="text-xs text-muted">{rupees(b.amount_paise)} paid · {b.seats.length} ticket{b.seats.length > 1 ? "s" : ""}</p>
          {b.checked_in_at && <p className="text-xs text-green-400 mt-1">Checked in</p>}
          {b.theatre.is_demo && (
            <p className="text-[11px] text-amber-300/90 text-center mt-4">Demo booking at a sample venue — this ticket isn&apos;t valid at a real cinema.</p>
          )}
        </div>
      </article>
      <div className="flex gap-2 mt-5">
        <button className="btn btn-ghost flex-1" onClick={() => window.print()}>Save / print</button>
        <Link className="btn btn-primary flex-1" href="/profile/">My tickets</Link>
      </div>
    </div>
  );
}
