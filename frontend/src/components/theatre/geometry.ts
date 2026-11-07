import type { Seat, SeatMap } from "@/lib/types";

export const EYE_HEIGHT = 1.15;

export interface Bounds {
  width: number; depth: number; height: number; maxZ: number; maxY: number;
  screenCenter: [number, number, number]; arcFocus: number;
}

export function roomBounds(map: SeatMap): Bounds {
  const seats = map.seats;
  const screen = map.auditorium.screen;
  const maxX = Math.max(...seats.map((s) => Math.abs(s.x)));
  const maxZ = Math.max(...seats.map((s) => s.z));
  const maxY = Math.max(...seats.map((s) => s.y));
  const width = Math.max(screen.width + 4, maxX * 2 + 4);
  return {
    width, depth: maxZ + 3, height: Math.max(screen.bottom + screen.height + 2.2, maxY + 5), maxZ, maxY,
    screenCenter: [0, screen.bottom + screen.height / 2, 0],
    arcFocus: guessArcFocus(seats),
  };
}

// arc focus isn't sent to the client; recover it from the outermost seat yaw
function guessArcFocus(seats: Seat[]) {
  const s = seats.reduce((a, b) => (Math.abs(b.yaw) > Math.abs(a.yaw) ? b : a), seats[0]);
  if (!s || Math.abs(s.yaw) < 1e-3) return 0;
  // seat on an arc: x = R sin(a), z = R cos(a) - F, yaw = a
  const r = s.x / Math.sin(s.yaw);
  return Math.max(0, r * Math.cos(s.yaw) - s.z);
}

export interface RowInfo { label: string; z: number; y: number; minX: number; maxX: number; depth: number }

export function rows(seats: Seat[]): RowInfo[] {
  const by = new Map<string, Seat[]>();
  seats.forEach((s) => by.set(s.row, [...(by.get(s.row) ?? []), s]));
  const out = [...by.entries()].map(([label, list]) => {
    const centre = list.reduce((a, b) => (Math.abs(b.x) < Math.abs(a.x) ? b : a));
    return { label, z: centre.z, y: centre.y, minX: Math.min(...list.map((s) => s.x)), maxX: Math.max(...list.map((s) => s.x)), depth: 1 };
  });
  out.sort((a, b) => a.z - b.z);
  out.forEach((r, i) => {
    const prev = out[i - 1]?.z ?? r.z - 1.2;
    const next = out[i + 1]?.z ?? r.z + 1.4;
    r.depth = (next - prev) / 2;
  });
  return out;
}
