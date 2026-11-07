import { Color } from "three";
import type { Theme } from "@/lib/types";

/**
 * Holds the *currently displayed* theme values and eases them toward the
 * target every frame. Meshes read from here inside useFrame, so a theme switch
 * (Dune -> Godzilla) is a smooth crossfade of the same auditorium, with zero
 * React re-renders and no scene rebuild.
 */
const COLOR_KEYS = [
  "primary", "secondary", "accent", "background", "surface", "ambient", "key", "rim", "wallWash",
  "floorGlow", "fog", "screenGlow", "fabric", "particle", "grad0", "grad1", "grad2",
] as const;
const NUM_KEYS = ["ambientI", "keyI", "rimI", "fogDensity", "screenI", "pulse", "pulseSpeed", "pDensity", "pSpeed"] as const;

type ColorKey = (typeof COLOR_KEYS)[number];
type NumKey = (typeof NUM_KEYS)[number];

function flatten(t: Theme): Record<ColorKey, string> & Record<NumKey, number> {
  const g = t.screen.idle_gradient;
  return {
    primary: t.palette.primary, secondary: t.palette.secondary, accent: t.palette.accent,
    background: t.palette.background, surface: t.palette.surface,
    ambient: t.lighting.ambient_color, key: t.lighting.key_color, rim: t.lighting.rim_color,
    wallWash: t.lighting.wall_wash, floorGlow: t.lighting.floor_glow,
    fog: t.fog.color, screenGlow: t.screen.glow_color, fabric: t.seat_fabric, particle: t.particles.color,
    grad0: g[0], grad1: g[1] ?? g[0], grad2: g[2] ?? g[1] ?? g[0],
    ambientI: t.lighting.ambient_intensity, keyI: t.lighting.key_intensity, rimI: t.lighting.rim_intensity,
    fogDensity: t.fog.density, screenI: t.screen.glow_intensity,
    pulse: t.animation.light_pulse, pulseSpeed: t.animation.pulse_speed,
    pDensity: t.particles.density, pSpeed: t.particles.speed,
  };
}

export class ThemeState {
  c = {} as Record<ColorKey, Color>;
  n = {} as Record<NumKey, number>;
  private tc = {} as Record<ColorKey, Color>;
  private tn = {} as Record<NumKey, number>;
  particleKind = "dust";
  targetParticleKind = "dust";
  particleFade = 1; // 0..1, dips to 0 while swapping particle type
  private k = 2.5;

  constructor(theme: Theme) {
    const f = flatten(theme);
    for (const key of COLOR_KEYS) {
      this.c[key] = new Color(f[key]);
      this.tc[key] = new Color(f[key]);
    }
    for (const key of NUM_KEYS) this.n[key] = this.tn[key] = f[key];
    this.particleKind = this.targetParticleKind = theme.particles.kind;
  }

  setTarget(theme: Theme, instant = false) {
    const f = flatten(theme);
    for (const key of COLOR_KEYS) this.tc[key].set(f[key]);
    for (const key of NUM_KEYS) this.tn[key] = f[key];
    this.targetParticleKind = theme.particles.kind;
    // ~95% of the way there after transition_ms
    this.k = 3 / Math.max(0.3, theme.animation.transition_ms / 1000);
    if (instant) {
      for (const key of COLOR_KEYS) this.c[key].copy(this.tc[key]);
      for (const key of NUM_KEYS) this.n[key] = this.tn[key];
      this.particleKind = this.targetParticleKind;
    }
  }

  update(dt: number) {
    const a = 1 - Math.exp(-this.k * Math.min(dt, 0.1));
    for (const key of COLOR_KEYS) this.c[key].lerp(this.tc[key], a);
    for (const key of NUM_KEYS) this.n[key] += (this.tn[key] - this.n[key]) * a;
    if (this.particleKind !== this.targetParticleKind) {
      this.particleFade = Math.max(0, this.particleFade - dt * 2.2);
      if (this.particleFade === 0) this.particleKind = this.targetParticleKind;
    } else if (this.particleFade < 1) {
      this.particleFade = Math.min(1, this.particleFade + dt * 1.2);
    }
  }
}
