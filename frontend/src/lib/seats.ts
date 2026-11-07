"use client";

import { create } from "zustand";
import { api, ApiError, WS_BASE } from "./api";
import { currentToken } from "./auth";
import type { Seat, SeatMap, SeatState } from "./types";

export const SEAT_COLORS: Record<SeatState | "selected", string> = {
  available: "#f4f6f8",
  selected: "#22c55e",
  held: "#f59e0b",
  booked: "#4b5563",
  blocked: "#1f2937",
};

export type DisplayState = SeatState | "selected" | "pending";

interface SeatStore {
  map: SeatMap | null;
  states: Record<string, { state: SeatState; tag: string | null }>;
  pending: Record<string, true>;
  focused: string | null; // seat shown in "view from my seat" / details
  hovered: string | null;
  deadline: number | null;
  viewers: number;
  connected: boolean;
  version: number; // bumps on any state change -> cheap subscription for the 3D scene
  error: string | null;
  load: (showId: string) => Promise<void>;
  apply: (changes: { seat_id: string; state: SeatState; tag?: string | null }[]) => void;
  replace: (all: { seat_id: string; state: SeatState; tag?: string | null }[]) => void;
  toggle: (seatId: string) => Promise<void>;
  holdMany: (ids: string[]) => Promise<void>;
  clearMine: () => Promise<void>;
  focus: (id: string | null) => void;
  hover: (id: string | null) => void;
  setError: (e: string | null) => void;
  reset: () => void;
}

export const useSeats = create<SeatStore>((set, get) => ({
  map: null, states: {}, pending: {}, focused: null, hovered: null, deadline: null,
  viewers: 1, connected: false, version: 0, error: null,

  load: async (showId) => {
    const map = await api<SeatMap>(`/shows/${showId}/seats`);
    const states: SeatStore["states"] = {};
    for (const s of map.seats) states[s.id] = { state: s.state, tag: s.tag };
    set({ map, states, deadline: map.hold_deadline_ms, version: get().version + 1 });
  },

  apply: (changes) => {
    if (!changes.length) return;
    const states = { ...get().states };
    for (const c of changes) states[c.seat_id] = { state: c.state, tag: c.tag ?? null };
    set({ states, version: get().version + 1 });
  },

  replace: (all) => {
    const states: SeatStore["states"] = {};
    for (const c of all) states[c.seat_id] = { state: c.state, tag: c.tag ?? null };
    set({ states, version: get().version + 1 });
  },

  toggle: async (seatId) => {
    const { map, states, pending } = get();
    if (!map || pending[seatId]) return;
    const cur = states[seatId];
    const mine = cur?.state === "held" && cur.tag === map.my_tag;
    if (!mine && cur?.state !== "available") return;
    if (!currentToken()) {
      set({ error: "login" });
      return;
    }
    set({ pending: { ...pending, [seatId]: true } });
    try {
      if (mine) {
        await api(`/shows/${map.show_id}/holds`, { method: "DELETE", body: { seat_ids: [seatId] } });
        get().apply([{ seat_id: seatId, state: "available" }]);
        if (!selectedIds(get()).length) set({ deadline: null });
      } else {
        const r = await api<{ deadline_ms: number }>(`/shows/${map.show_id}/holds`, { body: { seat_ids: [seatId] } });
        get().apply([{ seat_id: seatId, state: "held", tag: map.my_tag }]);
        set({ deadline: r.deadline_ms });
      }
    } catch (e) {
      const err = e as ApiError;
      if (err.code === "seat_taken") get().apply([{ seat_id: seatId, state: "held", tag: "other" }]);
      set({ error: err.message });
    } finally {
      const p = { ...get().pending };
      delete p[seatId];
      set({ pending: p });
    }
  },

  holdMany: async (ids) => {
    const { map } = get();
    if (!map) return;
    if (!currentToken()) {
      set({ error: "login" });
      return;
    }
    // swap the current selection for the recommended one
    await get().clearMine();
    try {
      const r = await api<{ deadline_ms: number; held: string[] }>(`/shows/${map.show_id}/holds`, { body: { seat_ids: ids } });
      get().apply(r.held.map((id) => ({ seat_id: id, state: "held" as const, tag: map.my_tag })));
      set({ deadline: r.deadline_ms });
    } catch (e) {
      set({ error: (e as ApiError).message });
      await get().load(map.show_id);
    }
  },

  clearMine: async () => {
    const s = get();
    const mine = selectedIds(s);
    if (!s.map || !mine.length) return;
    await api(`/shows/${s.map.show_id}/holds`, { method: "DELETE", body: { seat_ids: mine } }).catch(() => {});
    get().apply(mine.map((id) => ({ seat_id: id, state: "available" as const })));
    set({ deadline: null });
  },

  focus: (id) => set({ focused: id }),
  hover: (id) => (get().hovered === id ? undefined : set({ hovered: id })),
  setError: (error) => set({ error }),
  reset: () => set({ map: null, states: {}, pending: {}, focused: null, hovered: null, deadline: null, connected: false }),
}));

export function displayState(s: Pick<SeatStore, "map" | "states" | "pending">, id: string): DisplayState {
  if (s.pending[id]) return "pending";
  const st = s.states[id];
  if (!st) return "blocked";
  if (st.state === "held" && s.map?.my_tag && st.tag === s.map.my_tag) return "selected";
  return st.state;
}

export function selectedIds(s: Pick<SeatStore, "map" | "states">): string[] {
  const tag = s.map?.my_tag;
  if (!tag) return [];
  return Object.entries(s.states).filter(([, v]) => v.state === "held" && v.tag === tag).map(([k]) => k);
}

export function seatById(map: SeatMap | null, id: string | null): Seat | undefined {
  if (!map || !id) return undefined;
  return map.seats.find((s) => s.id === id);
}

/** Live updates. Reconnects with backoff; re-syncs from a fresh snapshot each time. */
export function connectSeatSocket(showId: string) {
  let ws: WebSocket | null = null;
  let closed = false;
  let attempt = 0;
  let ping: ReturnType<typeof setInterval> | undefined;

  const open = () => {
    const token = currentToken();
    ws = new WebSocket(`${WS_BASE}/ws/shows/${showId}${token ? `?token=${encodeURIComponent(token)}` : ""}`);
    ws.onopen = () => {
      attempt = 0;
      useSeats.setState({ connected: true });
      ping = setInterval(() => ws?.readyState === 1 && ws.send("ping"), 25000);
    };
    ws.onmessage = (ev) => {
      const msg = JSON.parse(ev.data);
      if (msg.type === "snapshot") useSeats.getState().replace(msg.seats);
      else if (msg.type === "seats") useSeats.getState().apply(msg.changes);
      else if (msg.type === "presence") useSeats.setState({ viewers: msg.viewers });
    };
    ws.onclose = () => {
      clearInterval(ping);
      useSeats.setState({ connected: false });
      if (closed) return;
      attempt += 1;
      setTimeout(open, Math.min(10000, 500 * 2 ** attempt));
    };
  };
  open();
  return () => {
    closed = true;
    clearInterval(ping);
    ws?.close();
  };
}
