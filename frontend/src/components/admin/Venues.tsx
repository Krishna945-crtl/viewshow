"use client";

import { useState } from "react";
import { DemoBadge, Spinner } from "@/components/ui/bits";
import { toast } from "@/components/ui/toast";
import { api, ApiError } from "@/lib/api";
import type { TheatreInfo } from "@/lib/types";
import { useApi } from "@/lib/useApi";

type T = TheatreInfo & { auditoriums: { id: string; name: string }[] };
const TEMPLATE = JSON.stringify({
  screen: { width: 12, height: 5, curvature: 0.1, distance: 5, bottom: 1.3 },
  aisle_width: 1.2, arc_focus: 18, rise_per_row: 0.3, flat_rows: 1,
  rows: [
    { label: "A", category: "standard", blocks: [4, 8, 4] },
    { label: "B", category: "standard", blocks: [4, 8, 4] },
    { label: "C", category: "premium", blocks: [4, 8, 4], accessible: [1] },
    { label: "D", category: "recliner", blocks: [2, 5, 2] },
  ],
}, null, 2);

interface Preview { summary: { seat_count: number; by_category: Record<string, number> }; seats: { label: string; category: string; x: number; z: number; blocked: boolean }[] }
const CAT_COLOR: Record<string, string> = { standard: "#9aa4b2", premium: "#5b8def", vip: "#c084fc", recliner: "#f2a65a" };

export default function Venues() {
  const { data: theatres, reload } = useApi<T[]>("/theatres");
  const [nt, setNt] = useState({ name: "", city: "", address: "" });
  const [target, setTarget] = useState<string | null>(null);
  const [audName, setAudName] = useState("Screen X");
  const [layout, setLayout] = useState(TEMPLATE);
  const [preview, setPreview] = useState<Preview | null>(null);

  async function addTheatre(e: React.FormEvent) {
    e.preventDefault();
    try {
      await api("/admin/theatres", { body: nt });
      setNt({ name: "", city: "", address: "" });
      reload();
    } catch (err) { toast((err as ApiError).message, "error"); }
  }
  const parsed = () => { try { return JSON.parse(layout); } catch { toast("Layout isn't valid JSON", "error"); return null; } };
  async function validate() {
    const l = parsed(); if (!l) return;
    try { setPreview(await api<Preview>("/admin/layouts/validate", { body: { name: audName, layout: l } })); }
    catch (err) { toast((err as ApiError).message, "error"); setPreview(null); }
  }
  async function create() {
    const l = parsed(); if (!l || !target) return;
    try {
      await api(`/admin/theatres/${target}/auditoriums`, { body: { name: audName, layout: l } });
      toast("Auditorium created with seats generated", "success");
      setTarget(null); setPreview(null); reload();
    } catch (err) { toast((err as ApiError).message, "error"); }
  }

  if (!theatres) return <Spinner />;
  const xs = preview?.seats.map((s) => s.x) ?? [0];
  const zs = preview?.seats.map((s) => s.z) ?? [0];
  const minX = Math.min(...xs) - 1, maxX = Math.max(...xs) + 1, maxZ = Math.max(...zs) + 1;

  return (
    <div className="space-y-4">
      <form onSubmit={addTheatre} className="glass rounded-2xl p-4 grid sm:grid-cols-4 gap-2 text-sm">
        <input required className="input" placeholder="Theatre name" value={nt.name} onChange={(e) => setNt({ ...nt, name: e.target.value })} />
        <input required className="input" placeholder="City" value={nt.city} onChange={(e) => setNt({ ...nt, city: e.target.value })} />
        <input className="input" placeholder="Address" value={nt.address} onChange={(e) => setNt({ ...nt, address: e.target.value })} />
        <button className="btn btn-primary">Register theatre</button>
        <p className="sm:col-span-4 text-[11px] text-muted">New venues are flagged as demo inventory. Real cinema inventory needs an authorised integration.</p>
      </form>
      <div className="grid md:grid-cols-2 gap-3">
        {theatres.map((t) => (
          <article key={t.id} className="glass rounded-2xl p-4">
            <div className="flex justify-between gap-2"><div><h3 className="font-semibold">{t.name}</h3><p className="text-xs text-muted">{t.city} · {t.address}</p></div>{t.is_demo && <DemoBadge />}</div>
            <div className="flex flex-wrap gap-1.5 mt-2">{t.auditoriums.map((a) => <span key={a.id} className="chip">{a.name}</span>)}</div>
            <button className="btn btn-ghost !min-h-8 !py-1 text-xs mt-3" onClick={() => { setTarget(t.id); setPreview(null); }}>+ Configure auditorium</button>
          </article>
        ))}
      </div>
      {target && (
        <section className="glass rounded-2xl p-4 grid lg:grid-cols-2 gap-4">
          <div className="space-y-2">
            <h3 className="font-semibold">Seat layout · {theatres.find((t) => t.id === target)?.name}</h3>
            <input className="input" value={audName} onChange={(e) => setAudName(e.target.value)} aria-label="Auditorium name" />
            <textarea className="input font-mono text-xs min-h-80" value={layout} onChange={(e) => setLayout(e.target.value)} aria-label="Layout JSON" spellCheck={false} />
            <p className="text-[11px] text-muted">blocks = seats per section, gaps between them become aisles. Categories: standard, premium, vip, recliner. Optional per row: blocked, accessible, gap_before.</p>
            <div className="flex gap-2"><button className="btn btn-ghost" onClick={validate}>Validate & preview</button><button className="btn btn-primary" onClick={create} disabled={!preview}>Create</button></div>
          </div>
          <div>
            {preview ? (
              <>
                <p className="text-sm">{preview.summary.seat_count} seats · {Object.entries(preview.summary.by_category).map(([k, v]) => `${v} ${k}`).join(", ")}</p>
                <svg viewBox={`${minX} -2 ${maxX - minX} ${maxZ + 2}`} className="w-full mt-2 bg-black/30 rounded-xl" role="img" aria-label="Top-down seat layout preview">
                  <rect x={-6} y={-1.2} width={12} height={0.25} fill="#fff" opacity="0.7" />
                  {preview.seats.map((s) => <rect key={s.label} x={s.x - 0.22} y={s.z - 0.22} width={0.44} height={0.44} rx={0.08} fill={s.blocked ? "#333" : CAT_COLOR[s.category]}><title>{s.label} · {s.category}</title></rect>)}
                </svg>
                <div className="flex gap-3 text-[11px] text-muted mt-2">{Object.entries(CAT_COLOR).map(([k, c]) => <span key={k} className="flex items-center gap-1"><span className="size-2.5 rounded-sm" style={{ background: c }} />{k}</span>)}</div>
              </>
            ) : <p className="text-sm text-muted">Validate to see a top-down preview.</p>}
          </div>
        </section>
      )}
    </div>
  );
}
