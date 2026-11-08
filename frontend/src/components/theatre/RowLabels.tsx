"use client";

import { Billboard } from "@react-three/drei";
import { useEffect, useMemo } from "react";
import { CanvasTexture, LinearMipmapLinearFilter, PlaneGeometry, SRGBColorSpace } from "three";
import type { Seat } from "@/lib/types";
import { useCam } from "./camera";

function letterTexture(label: string) {
  const c = document.createElement("canvas");
  c.width = c.height = 128;
  const g = c.getContext("2d")!;
  g.fillStyle = "rgba(10,12,16,0.82)";
  g.strokeStyle = "rgba(255,255,255,0.85)";
  g.lineWidth = 6;
  g.beginPath();
  g.roundRect(8, 8, 112, 112, 26);
  g.fill();
  g.stroke();
  g.fillStyle = "#fff";
  g.font = `800 ${label.length > 1 ? 54 : 70}px ui-sans-serif, system-ui, sans-serif`;
  g.textAlign = "center";
  g.textBaseline = "middle";
  g.fillText(label, 64, 68);
  const t = new CanvasTexture(c);
  t.colorSpace = SRGBColorSpace;
  t.minFilter = LinearMipmapLinearFilter;
  return t;
}

/** Row letters at both ends of every row, always facing the camera. Unlit, so themes can't wash them out. */
export default function RowLabels({ seats }: { seats: Seat[] }) {
  const seated = useCam((c) => c.view === "seat");

  const items = useMemo(() => {
    const byRow = new Map<string, Seat[]>();
    seats.forEach((s) => byRow.set(s.row, [...(byRow.get(s.row) ?? []), s]));
    const out: { key: string; label: string; pos: [number, number, number] }[] = [];
    byRow.forEach((list, row) => {
      const left = list.reduce((a, b) => (b.x < a.x ? b : a));
      const right = list.reduce((a, b) => (b.x > a.x ? b : a));
      // step outwards along the row's own curve (seat yaw), not straight sideways
      ([[left, -1], [right, 1]] as const).forEach(([s, dir]) => {
        const k = 0.8 * dir;
        out.push({ key: `${row}${dir}`, label: row, pos: [s.x + k * Math.cos(s.yaw), s.y + 0.75, s.z - k * Math.sin(s.yaw)] });
      });
    });
    return out;
  }, [seats]);

  const textures = useMemo(() => {
    const m = new Map<string, CanvasTexture>();
    items.forEach((i) => { if (!m.has(i.label)) m.set(i.label, letterTexture(i.label)); });
    return m;
  }, [items]);
  const plane = useMemo(() => new PlaneGeometry(0.56, 0.56), []);

  useEffect(() => () => {
    textures.forEach((t) => t.dispose());
  }, [textures]);
  useEffect(() => () => plane.dispose(), [plane]);

  return (
    <group visible={!seated}>
      {items.map((i) => (
        <Billboard key={i.key} position={i.pos}>
          <mesh geometry={plane} renderOrder={2}>
            <meshBasicMaterial map={textures.get(i.label)} transparent depthWrite={false} toneMapped={false} fog={false} />
          </mesh>
        </Billboard>
      ))}
    </group>
  );
}
