import { describe, expect, it } from "vitest";
import { DEFAULT_THEME } from "@/lib/theme";
import type { Seat, SeatMap, Theme } from "@/lib/types";
import { roomBounds, rows } from "./geometry";
import { ThemeState } from "./themeState";

const desert: Theme = structuredClone(DEFAULT_THEME);
desert.palette.primary = "#d08a32";
desert.particles.kind = "sand";
desert.animation.transition_ms = 1000;

describe("ThemeState transitions", () => {
  it("eases towards the target instead of jumping", () => {
    const t = new ThemeState(DEFAULT_THEME);
    const start = t.c.primary.getHexString();
    t.setTarget(desert);
    t.update(0.1);
    const mid = t.c.primary.getHexString();
    expect(mid).not.toBe(start);
    expect(mid).not.toBe("d08a32");
    for (let i = 0; i < 60; i++) t.update(0.05);
    expect(t.c.primary.getHexString()).toBe("d08a32");
  });

  it("fades particles out before swapping kind, then back in", () => {
    const t = new ThemeState(DEFAULT_THEME);
    t.setTarget(desert);
    t.update(0.1);
    expect(t.particleKind).toBe("dust");
    expect(t.particleFade).toBeLessThan(1);
    for (let i = 0; i < 20; i++) t.update(0.05);
    expect(t.particleKind).toBe("sand");
    for (let i = 0; i < 40; i++) t.update(0.05);
    expect(t.particleFade).toBe(1);
  });

  it("instant mode (reduced motion) applies immediately", () => {
    const t = new ThemeState(DEFAULT_THEME);
    t.setTarget(desert, true);
    expect(t.c.primary.getHexString()).toBe("d08a32");
    expect(t.particleKind).toBe("sand");
  });
});

function seat(row: string, n: number, x: number, z: number, yaw = 0, y = 0): Seat {
  return {
    id: `${row}${n}`, label: `${row}${n}`, row, number: n, category: "standard", block: 0, x, y, z, yaw,
    col: n, grid_row: row.charCodeAt(0) - 65, accessible: false, price_paise: 1, state: "available", tag: null,
    view: { score: 50, verdict: "", fov: 40, off_axis: 0, vertical: 0, distance: z },
  };
}

describe("auditorium geometry", () => {
  it("recovers the arc focus from curved seat positions", () => {
    const F = 20, z0 = 6, R = z0 + F, a = 0.2;
    const s = [seat("A", 1, Math.sin(-a) * R, Math.cos(a) * R - F, -a), seat("A", 2, 0, z0), seat("A", 3, Math.sin(a) * R, Math.cos(a) * R - F, a)];
    const map = { seats: s, auditorium: { screen: { width: 12, height: 5, curvature: 0, distance: 6, bottom: 1.2 } } } as unknown as SeatMap;
    expect(roomBounds(map).arcFocus).toBeCloseTo(F, 3);
  });

  it("orders rows front to back with sensible depths", () => {
    const r = rows([seat("B", 1, 0, 7, 0, 0.3), seat("A", 1, 0, 6), seat("C", 1, 0, 8.2, 0, 0.6)]);
    expect(r.map((x) => x.label)).toEqual(["A", "B", "C"]);
    expect(r[1].depth).toBeCloseTo(1.1, 5);
  });
});
