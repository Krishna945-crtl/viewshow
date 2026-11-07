"use client";

import { Html } from "@react-three/drei";
import { ThreeEvent, useFrame } from "@react-three/fiber";
import { useEffect, useMemo, useRef } from "react";
import {
  Color, InstancedBufferAttribute, InstancedMesh, MeshStandardMaterial, Object3D, PlaneGeometry,
} from "three";
import { rupees, cap } from "@/lib/format";
import { displayState, SEAT_COLORS, useSeats, type DisplayState } from "@/lib/seats";
import type { Seat, SeatCategory } from "@/lib/types";
import { platePose, seatGeometry } from "./seatGeometry";
import { plateMaterial } from "./plateMaterial";
import { useCam } from "./camera";
import { useThemeState } from "./context";

const CATS: SeatCategory[] = ["standard", "premium", "vip", "recliner"];
const INK_DARK = new Color("#0b0d10");
const INK_LIGHT = new Color("#e5e7eb");

// body tint per state (multiplied with the themed fabric colour)
const BODY_TINT: Record<DisplayState, Color> = {
  available: new Color(1, 1, 1),
  selected: new Color("#7dffa9"),
  pending: new Color("#c8ffd9"),
  held: new Color("#ffcf7a"),
  booked: new Color(0.32, 0.32, 0.34),
  blocked: new Color(0.18, 0.18, 0.2),
};
const PLATE: Record<DisplayState, { bg: Color; ink: Color }> = {
  available: { bg: new Color(SEAT_COLORS.available), ink: INK_DARK },
  selected: { bg: new Color(SEAT_COLORS.selected), ink: INK_DARK },
  pending: { bg: new Color("#86efac"), ink: INK_DARK },
  held: { bg: new Color(SEAT_COLORS.held), ink: INK_DARK },
  booked: { bg: new Color(SEAT_COLORS.booked), ink: INK_LIGHT },
  blocked: { bg: new Color(SEAT_COLORS.blocked), ink: new Color("#6b7280") },
};

interface Props {
  seats: Seat[];
  interactive: boolean;
  onSeatClick?: (seat: Seat) => void;
}

export default function Seats({ seats, interactive, onSeatClick }: Props) {
  const theme = useThemeState();
  const bodyRefs = useRef<Record<string, InstancedMesh | null>>({});
  const plateRef = useRef<InstancedMesh>(null);
  const hovered = useSeats((s) => s.hovered);
  const focused = useSeats((s) => s.focused);
  const version = useSeats((s) => s.version);
  const pending = useSeats((s) => s.pending);
  // seated view: number plates of the rows in front would block the screen
  const seated = useCam((c) => c.view === "seat");

  // group seat indices by category -> one InstancedMesh (one draw call) per category
  const groups = useMemo(() => {
    const g: Record<string, number[]> = {};
    seats.forEach((s, i) => (g[s.category] ??= []).push(i));
    return g;
  }, [seats]);

  const geos = useMemo(() => Object.fromEntries(CATS.map((c) => [c, seatGeometry(c)])), []);
  const bodyMat = useMemo(() => new MeshStandardMaterial({ roughness: 0.82, metalness: 0.05 }), []);
  const plateGeo = useMemo(() => new PlaneGeometry(0.34, 0.19), []);
  const plateMat = useMemo(() => plateMaterial(), []);
  const plateAttrs = useMemo(() => ({
    num: new InstancedBufferAttribute(new Float32Array(seats.length), 1),
    color: new InstancedBufferAttribute(new Float32Array(seats.length * 3), 3),
    ink: new InstancedBufferAttribute(new Float32Array(seats.length * 3), 3),
    glow: new InstancedBufferAttribute(new Float32Array(seats.length), 1),
  }), [seats.length]);

  useEffect(() => () => {
    Object.values(geos).forEach((g) => g.dispose());
    bodyMat.dispose();
    plateGeo.dispose();
    plateMat.dispose();
  }, [geos, bodyMat, plateGeo, plateMat]);

  // matrices - only when the layout changes
  useEffect(() => {
    const o = new Object3D();
    for (const cat of CATS) {
      const mesh = bodyRefs.current[cat];
      const idx = groups[cat];
      if (!mesh || !idx) continue;
      idx.forEach((si, i) => {
        const s = seats[si];
        o.position.set(s.x, s.y, s.z);
        o.rotation.set(0, s.yaw, 0);
        o.updateMatrix();
        mesh.setMatrixAt(i, o.matrix);
        mesh.setColorAt(i, BODY_TINT.available);
      });
      mesh.instanceMatrix.needsUpdate = true;
      mesh.computeBoundingSphere();
    }
    const plates = plateRef.current;
    if (plates) {
      const geo = plates.geometry;
      geo.setAttribute("aNum", plateAttrs.num);
      geo.setAttribute("aColor", plateAttrs.color);
      geo.setAttribute("aInk", plateAttrs.ink);
      geo.setAttribute("aGlow", plateAttrs.glow);
      seats.forEach((s, i) => {
        const pose = platePose(s.category);
        o.position.set(s.x, s.y + pose.y, s.z);
        o.rotation.set(0, s.yaw, 0);
        o.translateZ(pose.z);
        o.rotateX(-0.75); // tilt up so it reads from behind/above
        o.updateMatrix();
        plates.setMatrixAt(i, o.matrix);
        plateAttrs.num.setX(i, Math.min(100, s.number));
      });
      plates.instanceMatrix.needsUpdate = true;
      plateAttrs.num.needsUpdate = true;
      plates.computeBoundingSphere();
    }
  }, [seats, groups, plateAttrs]);

  // colours - whenever any seat state changes (websocket, my clicks...)
  useEffect(() => {
    const st = useSeats.getState();
    for (const cat of CATS) {
      const mesh = bodyRefs.current[cat];
      const idx = groups[cat];
      if (!mesh || !idx) continue;
      idx.forEach((si, i) => mesh.setColorAt(i, BODY_TINT[displayState(st, seats[si].id)]));
      if (mesh.instanceColor) mesh.instanceColor.needsUpdate = true;
    }
    seats.forEach((s, i) => {
      const p = PLATE[displayState(st, s.id)];
      plateAttrs.color.setXYZ(i, p.bg.r, p.bg.g, p.bg.b);
      plateAttrs.ink.setXYZ(i, p.ink.r, p.ink.g, p.ink.b);
      plateAttrs.glow.setX(i, s.id === hovered || s.id === focused ? 1 : 0);
    });
    plateAttrs.color.needsUpdate = plateAttrs.ink.needsUpdate = plateAttrs.glow.needsUpdate = true;
  }, [version, pending, hovered, focused, seats, groups, plateAttrs]);

  useFrame((state) => {
    bodyMat.color.copy(theme.c.fabric);
    bodyMat.emissive.copy(theme.c.fabric).multiplyScalar(0.18); // keep seats readable in dark themes
    plateMat.uniforms.uTime.value = state.clock.elapsedTime;
  });

  const seatFromEvent = (e: ThreeEvent<PointerEvent | MouseEvent>, cat?: string) => {
    if (e.instanceId === undefined) return undefined;
    return cat ? seats[groups[cat][e.instanceId]] : seats[e.instanceId];
  };

  const handlers = (cat?: string) =>
    interactive
      ? {
          onPointerMove: (e: ThreeEvent<PointerEvent>) => {
            e.stopPropagation();
            const s = seatFromEvent(e, cat);
            if (s) useSeats.getState().hover(s.id);
            document.body.style.cursor = "pointer";
          },
          onPointerOut: () => {
            useSeats.getState().hover(null);
            document.body.style.cursor = "";
          },
          onClick: (e: ThreeEvent<MouseEvent>) => {
            e.stopPropagation();
            if (e.delta > 8) return; // that was a camera drag, not a tap
            const s = seatFromEvent(e, cat);
            if (s) onSeatClick?.(s);
          },
        }
      : {};

  const tip = seats.find((s) => s.id === (hovered ?? focused));
  const tipState = tip ? displayState(useSeats.getState(), tip.id) : null;

  return (
    <group>
      {CATS.map((cat) =>
        groups[cat] ? (
          <instancedMesh
            key={cat}
            ref={(m) => {
              bodyRefs.current[cat] = m;
            }}
            args={[geos[cat], bodyMat, groups[cat].length]}
            frustumCulled={false}
            {...handlers(cat)}
          />
        ) : null,
      )}
      <instancedMesh ref={plateRef} args={[plateGeo, plateMat, seats.length]} frustumCulled={false} visible={!seated} {...handlers()} />
      {tip && interactive && !seated && (
        <Html position={[tip.x, tip.y + 1.75, tip.z]} center zIndexRange={[20, 0]} style={{ pointerEvents: "none" }}>
          <div className="glass rounded-xl px-3 py-2 text-xs whitespace-nowrap shadow-xl">
            <div className="font-semibold text-sm">
              {tip.label} · {cap(tip.category)}
            </div>
            <div className="text-muted">
              {rupees(tip.price_paise)} · {tip.view.verdict} ({tip.view.score})
            </div>
            <div className="mt-0.5 text-[11px] opacity-80">{stateText(tipState)}</div>
          </div>
        </Html>
      )}
    </group>
  );
}

function stateText(s: DisplayState | null) {
  switch (s) {
    case "selected": return "Selected by you";
    case "held": return "Someone is holding this seat";
    case "booked": return "Booked";
    case "blocked": return "Not available";
    case "pending": return "Updating…";
    default: return "Tap to select";
  }
}
