"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import HoldTimer from "@/components/seats/HoldTimer";
import Legend from "@/components/seats/Legend";
import Recommendations from "@/components/seats/Recommendations";
import SeatMap2D from "@/components/seats/SeatMap2D";
import SeatViewPanel from "@/components/seats/SeatViewPanel";
import { useCam, type CamView } from "@/components/theatre/camera";
import SoundControl from "@/components/ui/SoundControl";
import ThemeApplier from "@/components/ui/ThemeApplier";
import { DemoBadge, Empty, Spinner } from "@/components/ui/bits";
import { toast } from "@/components/ui/toast";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { rupees, showDate, showTime } from "@/lib/format";
import { usePrefs } from "@/lib/prefs";
import { connectSeatSocket, seatById, selectedIds, useSeats } from "@/lib/seats";
import type { Booking, Seat, ShowDetail } from "@/lib/types";
import { useApi } from "@/lib/useApi";
import { detectGpu } from "@/lib/webgl";

const Auditorium3D = dynamic(() => import("@/components/theatre/Auditorium3D"), {
  ssr: false,
  loading: () => <div className="absolute inset-0 grid place-items-center text-muted text-sm">Building the auditorium…</div>,
});

const VIEWS: { id: CamView; label: string }[] = [
  { id: "overview", label: "Overview" },
  { id: "back", label: "Back row" },
  { id: "side", label: "Side" },
  { id: "stage", label: "From stage" },
];

export default function SeatSelection() {
  const showId = useSearchParams().get("show") ?? "";
  const router = useRouter();
  const session = useAuth((s) => s.session);
  const authReady = useAuth((s) => s.ready);
  const prefs = usePrefs();
  const { data: show, error: showErr } = useApi<ShowDetail>(showId ? `/shows/${showId}` : null);
  const map = useSeats((s) => s.map);
  const focused = useSeats((s) => s.focused);
  const deadline = useSeats((s) => s.deadline);
  const viewers = useSeats((s) => s.viewers);
  const connected = useSeats((s) => s.connected);
  const err = useSeats((s) => s.error);
  useSeats((s) => s.version);
  const cam = useCam();
  const [gpu, setGpu] = useState<"none" | "low" | "high" | null>(null);
  const [slow, setSlow] = useState(false);
  const [panel, setPanel] = useState<"seat" | "recs" | null>(null);
  const [settings, setSettings] = useState(false);
  const [busy, setBusy] = useState(false);

  useEffect(() => setGpu(detectGpu()), []);
  const mode = gpu === "none" ? "2d" : prefs.viewMode;

  // load + live updates (re-run when login state changes so "mine" is right)
  useEffect(() => {
    if (!showId || !authReady) return;
    let stop: (() => void) | undefined;
    useSeats.getState().load(showId).then(() => (stop = connectSeatSocket(showId))).catch((e: ApiError) => toast(e.message, "error"));
    return () => {
      stop?.();
      useSeats.getState().reset();
      useCam.getState().go("overview");
    };
  }, [showId, authReady, session?.user.id]);

  useEffect(() => {
    if (!err) return;
    if (err === "login") {
      toast("Sign in to pick seats — we'll bring you right back.");
      router.push(`/login/?next=${encodeURIComponent(`/seats/?show=${showId}`)}`);
    } else toast(err, "error");
    useSeats.getState().setError(null);
  }, [err, router, showId]);

  const selected = map ? selectedIds({ map, states: useSeats.getState().states }) : [];
  const selectedSeats = selected.map((id) => seatById(map, id)!).filter(Boolean);
  const total = selectedSeats.reduce((a, s) => a + s.price_paise, 0);
  const focusSeat = seatById(map, focused);

  const onSeatClick = useCallback((s: Seat) => {
    useSeats.getState().focus(s.id);
    setPanel("seat");
    useSeats.getState().toggle(s.id);
  }, []);

  const viewFrom = (id: string) => {
    useSeats.getState().focus(id);
    setPanel("seat");
    if (mode === "2d") prefs.set({ viewMode: "3d" });
    cam.go("seat", id);
  };

  const stepSeat = (dir: -1 | 1) => {
    if (!map || !focusSeat) return;
    const row = map.seats.filter((s) => s.row === focusSeat.row).sort((a, b) => a.number - b.number);
    const next = row[(row.findIndex((s) => s.id === focusSeat.id) + dir + row.length) % row.length];
    useSeats.getState().focus(next.id);
    if (cam.view === "seat") cam.go("seat", next.id);
  };

  const onExpire = useCallback(() => {
    toast("Your seat hold expired — the seats are back on sale.", "error");
    useSeats.getState().load(showId);
  }, [showId]);

  async function proceed() {
    setBusy(true);
    try {
      const b = await api<Booking>("/bookings", { body: { show_id: showId, seat_ids: selected } });
      router.push(`/checkout/?booking=${b.id}`);
    } catch (e) {
      toast((e as ApiError).message, "error");
      useSeats.getState().load(showId);
    } finally {
      setBusy(false);
    }
  }

  const theme = show?.movie.theme;
  const sortedLabels = selectedSeats.map((s) => s.label).sort();

  if (showErr) return <Empty title="Show not found" hint={showErr.message}><Link className="btn btn-ghost" href="/home/">Back to movies</Link></Empty>;
  if (!show || !map) return <><ThemeApplier theme={theme} /><Spinner label="Opening the auditorium" /></>;

  return (
    <div className="fixed inset-0 flex flex-col" style={{ paddingTop: "env(safe-area-inset-top)" }}>
      <ThemeApplier theme={theme} />
      {/* header */}
      <header className="glass border-x-0 border-t-0 z-20">
        <div className="px-3 sm:px-5 h-14 flex items-center gap-3">
          <Link href={`/showtimes/?movie=${show.movie.slug}`} className="btn btn-ghost !min-h-9 !px-3" aria-label="Back to showtimes">←</Link>
          <div className="min-w-0">
            <h1 className="font-semibold truncate leading-tight">{show.movie.title}</h1>
            <p className="text-[11px] text-muted truncate">
              {show.theatre.name} · {show.auditorium.name} · {showDate(show.starts_at)} {showTime(show.starts_at)}
            </p>
          </div>
          {show.theatre.is_demo && <span className="hidden md:inline"><DemoBadge /></span>}
          <div className="ml-auto flex items-center gap-2">
            <span className="hidden sm:flex items-center gap-1.5 text-[11px] text-muted" title={connected ? "Live" : "Reconnecting"}>
              <span className={`size-2 rounded-full ${connected ? "bg-green-400" : "bg-amber-400 animate-pulse"}`} />
              {viewers} viewing
            </span>
            <SoundControl preset={theme?.sound.preset ?? "none"} />
            <div className="flex rounded-full border border-line p-0.5" role="radiogroup" aria-label="Seat view mode">
              {(["3d", "2d"] as const).map((m) => (
                <button key={m} role="radio" aria-checked={mode === m} disabled={m === "3d" && gpu === "none"}
                  onClick={() => prefs.set({ viewMode: m })}
                  className={`px-3 py-1 rounded-full text-xs font-semibold ${mode === m ? "bg-primary text-white" : "text-muted"}`}>
                  {m.toUpperCase()}
                </button>
              ))}
            </div>
            <button className="btn btn-ghost !min-h-9 !px-3" aria-label="Display settings" aria-expanded={settings} onClick={() => setSettings(!settings)}>⚙</button>
          </div>
        </div>
        {settings && (
          <div className="px-4 pb-3 flex flex-wrap gap-2 text-xs">
            <button className="chip" aria-pressed={prefs.reduceMotion} onClick={() => prefs.set({ reduceMotion: !prefs.reduceMotion })}>Reduce motion</button>
            <button className="chip" aria-pressed={prefs.highContrast} onClick={() => prefs.set({ highContrast: !prefs.highContrast })}>High contrast</button>
            {(["auto", "high", "low"] as const).map((q) => (
              <button key={q} className="chip" aria-pressed={prefs.quality === q} onClick={() => prefs.set({ quality: q })}>3D quality: {q}</button>
            ))}
          </div>
        )}
      </header>

      {/* stage */}
      <div className="relative flex-1 min-h-0">
        {mode === "3d" ? (
          <>
            <Auditorium3D map={map} theme={show.movie.theme} onSeatClick={onSeatClick} onSlow={() => setSlow(true)} className="absolute inset-0" />
            <div className="absolute top-3 left-3 right-3 flex flex-wrap gap-1.5 pointer-events-none">
              {cam.view === "seat" ? (
                <button className="chip glass pointer-events-auto !bg-primary !text-white" onClick={() => cam.go("overview")}>
                  ✕ Exit view from {focusSeat?.label}
                </button>
              ) : VIEWS.map((v) => (
                <button key={v.id} className="chip glass pointer-events-auto" aria-pressed={cam.view === v.id} onClick={() => cam.go(v.id)}>{v.label}</button>
              ))}
              <button className="chip glass pointer-events-auto" onClick={() => cam.go("overview")} aria-label="Reset camera">⟲ Reset</button>
            </div>
            {cam.view === "seat" && focusSeat && (
              <div className="absolute top-14 left-1/2 -translate-x-1/2 glass rounded-full px-4 py-1.5 text-xs pointer-events-none">
                Seated view · {focusSeat.label} · drag to look around
              </div>
            )}
            {slow && (
              <div className="absolute bottom-3 left-3 right-3 sm:right-auto glass rounded-2xl p-3 text-sm flex items-center gap-3">
                <span>3D is running slowly on this device.</span>
                <button className="btn btn-primary !min-h-8 !py-1" onClick={() => { prefs.set({ viewMode: "2d" }); setSlow(false); }}>Use 2D</button>
                <button className="text-muted" onClick={() => setSlow(false)} aria-label="Dismiss">×</button>
              </div>
            )}
          </>
        ) : (
          <div className="absolute inset-0 overflow-auto px-2">
            {gpu === "none" && <p className="text-center text-xs text-amber-300 mt-3">3D needs WebGL, which isn&apos;t available here — the 2D map has everything you need.</p>}
            <SeatMap2D seats={map.seats} onSeatClick={onSeatClick} />
          </div>
        )}

        {/* side panels */}
        <div className="absolute right-3 bottom-3 sm:top-14 sm:bottom-auto left-3 sm:left-auto flex flex-col gap-2 items-end pointer-events-none">
          {panel === "seat" && focusSeat && (
            <div className="pointer-events-auto w-full sm:w-auto">
              <SeatViewPanel seat={focusSeat} verified={map.auditorium.dimensions_verified} inSeatView={cam.view === "seat"}
                onView={() => viewFrom(focusSeat.id)} onExit={() => cam.go("overview")} onToggle={() => useSeats.getState().toggle(focusSeat.id)}
                onStep={stepSeat} onClose={() => { setPanel(null); useSeats.getState().focus(null); }} />
            </div>
          )}
          {panel === "recs" && (
            <div className="pointer-events-auto w-full sm:w-auto">
              <Recommendations showId={showId} onPreview={viewFrom} onClose={() => setPanel(null)} />
            </div>
          )}
        </div>
      </div>

      {/* footer */}
      <footer className="glass border-x-0 border-b-0 z-20" style={{ paddingBottom: "env(safe-area-inset-bottom)" }}>
        <div className="px-3 sm:px-5 py-2.5 flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-4">
          <div className="hidden lg:block"><Legend prices={map.prices} /></div>
          <div className="flex items-center gap-2 sm:ml-auto">
            <button className="btn btn-ghost !min-h-10 text-sm" onClick={() => setPanel(panel === "recs" ? null : "recs")}>✨ Best seats</button>
            <HoldTimer deadline={selected.length ? deadline : null} onExpire={onExpire} />
            <div className="text-sm ml-auto sm:ml-0 text-right">
              <div className="font-semibold" aria-live="polite">
                {selected.length ? `${selected.length} seat${selected.length > 1 ? "s" : ""} · ${rupees(total)}` : "No seats selected"}
              </div>
              <div className="text-[11px] text-muted truncate max-w-40">{sortedLabels.join(", ")}</div>
            </div>
            <button className="btn btn-primary" disabled={!selected.length || busy} onClick={proceed}>{busy ? "Holding…" : "Continue"}</button>
          </div>
        </div>
      </footer>
    </div>
  );
}
