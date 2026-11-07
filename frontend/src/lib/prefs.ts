"use client";

import { create } from "zustand";
import { load, save } from "./storage";

export type ViewMode = "3d" | "2d";
export type Quality = "auto" | "high" | "low";

interface Prefs {
  viewMode: ViewMode;
  reduceMotion: boolean;
  highContrast: boolean;
  soundOn: boolean;
  volume: number;
  quality: Quality;
  city: string;
  onboarded: boolean;
  hydrated: boolean;
  hydrate: () => void;
  set: (p: Partial<Omit<Prefs, "set" | "hydrate" | "hydrated">>) => void;
}

const KEYS = ["viewMode", "reduceMotion", "highContrast", "soundOn", "volume", "quality", "city", "onboarded"] as const;

export const usePrefs = create<Prefs>((set, get) => ({
  viewMode: "3d",
  reduceMotion: false,
  highContrast: false,
  soundOn: false, // sound is always opt-in
  volume: 0.35,
  quality: "auto",
  city: "Hyderabad",
  onboarded: false,
  hydrated: false,
  hydrate: () => {
    const stored = load<Partial<Prefs>>("cv.prefs", {});
    const sysReduce = typeof window !== "undefined" && window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
    // never restore soundOn - autoplaying audio on page load is rude
    set({ ...stored, soundOn: false, reduceMotion: stored.reduceMotion ?? !!sysReduce, hydrated: true });
    apply(get());
  },
  set: (p) => {
    set(p);
    const s = get();
    save("cv.prefs", Object.fromEntries(KEYS.map((k) => [k, s[k]])));
    apply(s);
  },
}));

function apply(p: Prefs) {
  if (typeof document === "undefined") return;
  document.documentElement.classList.toggle("reduce-motion", p.reduceMotion);
  document.documentElement.classList.toggle("high-contrast", p.highContrast);
}
