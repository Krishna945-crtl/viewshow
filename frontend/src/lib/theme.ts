import type { Theme } from "./types";

export const DEFAULT_THEME: Theme = {
  name: "CineVerse",
  source: "auto",
  archetypes: [],
  mood: "house style",
  palette: { primary: "#7c5cff", secondary: "#1a1440", accent: "#5fe1ff", background: "#07070b", surface: "#12121a" },
  lighting: {
    ambient_color: "#b3a6ff", ambient_intensity: 0.45, key_color: "#d8d0ff", key_intensity: 1.1,
    rim_color: "#5fe1ff", rim_intensity: 0.8, wall_wash: "#7c5cff", floor_glow: "#5fe1ff",
  },
  fog: { color: "#241c55", density: 0.016 },
  screen: { glow_color: "#c9bcff", glow_intensity: 0.9, idle_gradient: ["#0d0a24", "#7c5cff", "#5fe1ff"] },
  particles: { kind: "dust", density: 0.4, color: "#5fe1ff", speed: 0.5 },
  animation: { light_pulse: 0.2, pulse_speed: 0.6, transition_ms: 1800 },
  sound: { preset: "none", default_volume: 0.35 },
  seat_fabric: "#2a2350",
};

export function applyThemeToDocument(t: Theme) {
  if (typeof document === "undefined") return;
  const r = document.documentElement.style;
  r.setProperty("--cv-primary", t.palette.primary);
  r.setProperty("--cv-secondary", t.palette.secondary);
  r.setProperty("--cv-accent", t.palette.accent);
  r.setProperty("--cv-bg", t.palette.background);
  r.setProperty("--cv-surface", t.palette.surface);
  document.querySelector('meta[name="theme-color"]')?.setAttribute("content", t.palette.background);
}

// tiny hash -> stable pseudo random, used for procedural poster art
export function hashString(s: string) {
  let h = 2166136261;
  for (let i = 0; i < s.length; i++) {
    h ^= s.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return h >>> 0;
}
