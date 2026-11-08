"use client";

import dynamic from "next/dynamic";
import { useState } from "react";
import { Spinner } from "@/components/ui/bits";
import { toast } from "@/components/ui/toast";
import { api, ApiError } from "@/lib/api";
import { useDemoMap } from "@/lib/demoMap";
import { DEFAULT_THEME } from "@/lib/theme";
import type { Theme } from "@/lib/types";
import { useApi } from "@/lib/useApi";

const Auditorium3D = dynamic(() => import("@/components/theatre/Auditorium3D"), { ssr: false });
const PARTICLES = ["none", "dust", "sand", "embers", "bubbles", "stars", "snow", "rain", "sparks", "petals", "leaves", "mist"];
const SOUNDS = ["none", "desert_wind", "deep_ocean", "space_hum", "rain", "forest", "ember_crackle", "city_night", "cavern", "heartbeat", "music_box", "stadium", "lounge", "temple_bells"];

type Row = { id: string; name: string; config: Theme };

export default function Themes() {
  const { data: themes, reload } = useApi<Row[]>("/admin/themes");
  const map = useDemoMap();
  const [cur, setCur] = useState<{ id?: string; name: string; config: Theme } | null>(null);

  if (!themes) return <Spinner />;
  const t = cur?.config;
  const upd = (path: string, value: unknown) => {
    if (!cur) return;
    const next = structuredClone(cur.config) as unknown as Record<string, Record<string, unknown>>;
    const [a, b] = path.split(".");
    if (b) next[a][b] = value;
    else (next as Record<string, unknown>)[a] = value;
    setCur({ ...cur, config: next as unknown as Theme });
  };

  async function save() {
    if (!cur) return;
    try {
      const r = await api<Row>(cur.id ? `/admin/themes/${cur.id}` : "/admin/themes", { method: cur.id ? "PUT" : "POST", body: { name: cur.name, config: cur.config } });
      setCur({ id: r.id, name: r.name, config: r.config }); // server-clamped values come back
      toast("Theme saved (values were safety-clamped where needed)", "success");
      reload();
    } catch (e) {
      toast((e as ApiError).message, "error");
    }
  }

  const color = (label: string, path: string, v: string) => (
    <label className="flex items-center justify-between gap-2 text-xs">{label}
      <input type="color" value={v} onChange={(e) => upd(path, e.target.value)} className="h-8 w-12 rounded bg-transparent" />
    </label>
  );
  const slider = (label: string, path: string, v: number, min: number, max: number, step: number) => (
    <label className="block text-xs">{label} <span className="text-muted">{v.toFixed(3)}</span>
      <input type="range" min={min} max={max} step={step} value={v} onChange={(e) => upd(path, Number(e.target.value))} className="w-full accent-[var(--cv-accent)]" />
    </label>
  );

  return (
    <div className="grid lg:grid-cols-[240px_1fr] gap-4">
      <aside className="space-y-2">
        <button className="btn btn-primary w-full" onClick={() => setCur({ name: "New theme", config: structuredClone(DEFAULT_THEME) })}>+ New theme</button>
        {themes.map((r) => (
          <button key={r.id} className={`w-full text-left glass rounded-xl p-3 flex items-center gap-2 ${cur?.id === r.id ? "ring-2 ring-accent" : ""}`} onClick={() => setCur(structuredClone(r))}>
            <span className="size-4 rounded" style={{ background: r.config.palette.primary }} />{r.name}
          </button>
        ))}
        <p className="text-[11px] text-muted">Movies without a theme get one generated automatically from genre, mood tags and synopsis.</p>
      </aside>
      {cur && t ? (
        <div className="grid xl:grid-cols-[1fr_300px] gap-4">
          <div className="relative rounded-2xl overflow-hidden border border-line h-[46vh] min-h-72">
            {map ? <Auditorium3D map={map} theme={t} interactive={false} className="absolute inset-0" /> : <Spinner label="Loading preview" />}
          </div>
          <div className="glass rounded-2xl p-4 space-y-3 max-h-[70vh] overflow-auto">
            <input className="input" value={cur.name} onChange={(e) => setCur({ ...cur, name: e.target.value })} aria-label="Theme name" />
            <fieldset className="space-y-1.5"><legend className="text-xs font-semibold mb-1">Palette</legend>
              {color("Primary", "palette.primary", t.palette.primary)}{color("Secondary", "palette.secondary", t.palette.secondary)}
              {color("Accent", "palette.accent", t.palette.accent)}{color("Background", "palette.background", t.palette.background)}
              {color("Seat fabric", "seat_fabric", t.seat_fabric)}
            </fieldset>
            <fieldset className="space-y-1.5"><legend className="text-xs font-semibold mb-1">Lighting</legend>
              {color("Ambient", "lighting.ambient_color", t.lighting.ambient_color)}{slider("Ambient intensity", "lighting.ambient_intensity", t.lighting.ambient_intensity, 0.25, 0.9, 0.01)}
              {color("Key light", "lighting.key_color", t.lighting.key_color)}{slider("Key intensity", "lighting.key_intensity", t.lighting.key_intensity, 0.4, 2, 0.05)}
              {color("Wall wash", "lighting.wall_wash", t.lighting.wall_wash)}{slider("Rim intensity", "lighting.rim_intensity", t.lighting.rim_intensity, 0, 1.6, 0.05)}
              {color("Step lights", "lighting.floor_glow", t.lighting.floor_glow)}
            </fieldset>
            <fieldset className="space-y-1.5"><legend className="text-xs font-semibold mb-1">Atmosphere</legend>
              {color("Fog", "fog.color", t.fog.color)}{slider("Fog density", "fog.density", t.fog.density, 0, 0.035, 0.001)}
              {color("Screen glow", "screen.glow_color", t.screen.glow_color)}
              <label className="block text-xs">Particles
                <select className="input mt-1 !py-1.5" value={t.particles.kind} onChange={(e) => upd("particles.kind", e.target.value)}>{PARTICLES.map((p) => <option key={p}>{p}</option>)}</select>
              </label>
              {color("Particle colour", "particles.color", t.particles.color)}{slider("Particle density", "particles.density", t.particles.density, 0, 1, 0.05)}
              {slider("Light pulse", "animation.light_pulse", t.animation.light_pulse, 0, 0.6, 0.01)}
              {slider("Transition (ms)", "animation.transition_ms", t.animation.transition_ms, 300, 4000, 100)}
              <label className="block text-xs">Ambience
                <select className="input mt-1 !py-1.5" value={t.sound.preset} onChange={(e) => upd("sound.preset", e.target.value)}>{SOUNDS.map((p) => <option key={p}>{p}</option>)}</select>
              </label>
            </fieldset>
            <p className="text-[11px] text-muted">Seat status colours are fixed and can&apos;t be themed — that keeps availability readable everywhere.</p>
            <div className="flex gap-2">
              <button className="btn btn-primary flex-1" onClick={save}>Save</button>
              {cur.id && <button className="btn btn-ghost" onClick={async () => { await api(`/admin/themes/${cur.id}`, { method: "DELETE" }); setCur(null); reload(); }}>Delete</button>}
            </div>
          </div>
        </div>
      ) : <p className="text-muted text-sm">Pick a theme to edit — changes preview live in the 3D hall.</p>}
    </div>
  );
}
