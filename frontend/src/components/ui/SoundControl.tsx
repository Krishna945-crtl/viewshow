"use client";

import { useEffect } from "react";
import { ambience } from "@/lib/ambience";
import { usePrefs } from "@/lib/prefs";

export default function SoundControl({ preset }: { preset: string }) {
  const { soundOn, volume, set } = usePrefs();

  useEffect(() => {
    if (!ambience) return;
    if (soundOn) ambience.play(preset);
    else ambience.stop();
  }, [soundOn, preset]);
  useEffect(() => ambience?.setVolume(volume), [volume]);
  useEffect(() => () => ambience?.stop(), []);

  if (preset === "none") return null;
  return (
    <div className="flex items-center gap-2">
      <button className="btn btn-ghost !min-h-9 !px-3 !py-1.5 text-xs" aria-pressed={soundOn}
              onClick={() => set({ soundOn: !soundOn })} title="Theme ambience">
        {soundOn ? "🔊" : "🔇"} <span className="hidden md:inline">Ambience</span>
      </button>
      {soundOn && (
        <input type="range" min={0} max={1} step={0.05} value={volume} aria-label="Ambience volume"
               onChange={(e) => set({ volume: Number(e.target.value) })} className="w-20 accent-[var(--cv-accent)]" />
      )}
    </div>
  );
}
