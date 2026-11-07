"use client";

import { useFrame } from "@react-three/fiber";
import { useEffect, useMemo, useRef } from "react";
import {
  BoxGeometry, BufferGeometry, ExtrudeGeometry, InstancedMesh, MeshBasicMaterial, MeshStandardMaterial, Object3D,
  Shape,
} from "three";
import { mergeGeometries } from "three/examples/jsm/utils/BufferGeometryUtils.js";
import type { Seat } from "@/lib/types";
import { useThemeState } from "./context";
import { Bounds, rows } from "./geometry";

/** A slab between two arcs (or a plain box when rows are straight). */
function riserGeometry(focus: number, zFront: number, zBack: number, halfWidth: number, height: number) {
  if (focus <= 0) {
    const g = new BoxGeometry(halfWidth * 2, height, zBack - zFront);
    g.translate(0, height / 2, (zFront + zBack) / 2);
    return g;
  }
  const r1 = zFront + focus;
  const r2 = zBack + focus;
  const span = Math.min(1.2, (halfWidth + 0.6) / r1);
  const shape = new Shape();
  const steps = 28;
  // world (x, z) -> shape (x, -z) because of the rotateX below
  for (let i = 0; i <= steps; i++) {
    const a = -span + (2 * span * i) / steps;
    const x = Math.sin(a) * r1, z = Math.cos(a) * r1 - focus;
    if (i === 0) shape.moveTo(x, -z);
    else shape.lineTo(x, -z);
  }
  for (let i = steps; i >= 0; i--) {
    const a = -span + (2 * span * i) / steps;
    shape.lineTo(Math.sin(a) * r2, -(Math.cos(a) * r2 - focus));
  }
  const g = new ExtrudeGeometry(shape, { depth: height, bevelEnabled: false, curveSegments: 1 });
  g.rotateX(-Math.PI / 2);
  return g;
}

export default function Room({ seats, bounds }: { seats: Seat[]; bounds: Bounds }) {
  const theme = useThemeState();
  const { width, depth, height, arcFocus } = bounds;
  const half = width / 2;

  const { risers, lips } = useMemo(() => {
    const parts: BufferGeometry[] = [];
    const strips: BufferGeometry[] = [];
    const rs = rows(seats);
    rs.forEach((r, i) => {
      if (r.y <= 0.001) return;
      const zFront = (rs[i - 1] ? (rs[i - 1].z + r.z) / 2 : r.z - 0.6);
      const zBack = i === rs.length - 1 ? depth : (r.z + rs[i + 1].z) / 2;
      parts.push(riserGeometry(arcFocus, zFront, zBack, half - 0.4, r.y));
      // glowing step nosing on the front edge of each riser
      const lip = riserGeometry(arcFocus, zFront - 0.015, zFront + 0.03, half - 0.45, 0.03);
      lip.translate(0, r.y - 0.03, 0);
      strips.push(lip);
    });
    const risers = parts.length ? mergeGeometries(parts.map((g) => g.toNonIndexed()), false) : null;
    const lips = strips.length ? mergeGeometries(strips.map((g) => g.toNonIndexed()), false) : null;
    [...parts, ...strips].forEach((g) => g.dispose());
    return { risers, lips };
  }, [seats, depth, half, arcFocus]);

  const wallMat = useMemo(() => new MeshStandardMaterial({ roughness: 0.95, metalness: 0 }), []);
  const floorMat = useMemo(() => new MeshStandardMaterial({ roughness: 0.9 }), []);
  const riserMat = useMemo(() => new MeshStandardMaterial({ roughness: 0.85 }), []);
  const glowMat = useMemo(() => new MeshBasicMaterial({ toneMapped: false }), []);
  const washMat = useMemo(() => new MeshBasicMaterial({ toneMapped: false, transparent: true, opacity: 0.9 }), []);
  const boothMat = useMemo(() => new MeshBasicMaterial({ toneMapped: false }), []);
  const panelRef = useRef<InstancedMesh>(null);
  const sconceRef = useRef<InstancedMesh>(null);

  const panelCount = Math.max(2, Math.floor(depth / 2.6)) * 2;
  useEffect(() => {
    const o = new Object3D();
    const per = panelCount / 2;
    for (let i = 0; i < per; i++) {
      const z = 0.8 + ((depth - 1.6) * (i + 0.5)) / per;
      [-1, 1].forEach((side, k) => {
        o.position.set(side * (half - 0.12), height * 0.45, z);
        o.rotation.set(0, 0, 0);
        o.updateMatrix();
        panelRef.current?.setMatrixAt(i * 2 + k, o.matrix);
        o.position.set(side * (half - 0.06), height * 0.45, z);
        o.updateMatrix();
        sconceRef.current?.setMatrixAt(i * 2 + k, o.matrix);
      });
    }
    if (panelRef.current) panelRef.current.instanceMatrix.needsUpdate = true;
    if (sconceRef.current) sconceRef.current.instanceMatrix.needsUpdate = true;
  }, [panelCount, depth, half, height]);

  useEffect(() => () => {
    risers?.dispose();
    lips?.dispose();
  }, [risers, lips]);

  useFrame((state) => {
    const t = state.clock.elapsedTime;
    const pulse = 1 + theme.n.pulse * 0.35 * Math.sin(t * theme.n.pulseSpeed * Math.PI * 2);
    wallMat.color.copy(theme.c.surface).multiplyScalar(0.75);
    floorMat.color.copy(theme.c.background).lerp(theme.c.secondary, 0.25);
    riserMat.color.copy(theme.c.surface).lerp(theme.c.secondary, 0.4);
    glowMat.color.copy(theme.c.floorGlow).multiplyScalar(0.9 * pulse);
    washMat.color.copy(theme.c.wallWash).multiplyScalar(0.85 * pulse);
    boothMat.color.copy(theme.c.screenGlow).multiplyScalar(0.6);
  });

  const stageDepth = 1.6;
  return (
    <group>
      {/* floor */}
      <mesh rotation-x={-Math.PI / 2} position={[0, 0, (depth - stageDepth) / 2]} material={floorMat}>
        <planeGeometry args={[width, depth + stageDepth]} />
      </mesh>
      {risers && <mesh geometry={risers} material={riserMat} />}
      {lips && <mesh geometry={lips} material={glowMat} />}
      {/* stage under the screen */}
      <mesh position={[0, 0.25, -stageDepth / 2]} material={riserMat}>
        <boxGeometry args={[width - 0.4, 0.5, stageDepth]} />
      </mesh>
      <mesh position={[0, 0.5, 0.01]} material={glowMat}>
        <boxGeometry args={[width - 0.6, 0.025, 0.03]} />
      </mesh>
      {/* walls */}
      {[-1, 1].map((side) => (
        <mesh key={side} position={[side * half, height / 2, (depth - stageDepth) / 2]} material={wallMat}>
          <boxGeometry args={[0.2, height, depth + stageDepth]} />
        </mesh>
      ))}
      <mesh position={[0, height / 2, depth]} material={wallMat}>
        <boxGeometry args={[width, height, 0.2]} />
      </mesh>
      <mesh position={[0, height / 2, -stageDepth - 0.05]} material={wallMat}>
        <boxGeometry args={[width, height, 0.1]} />
      </mesh>
      <mesh position={[0, height, (depth - stageDepth) / 2]} rotation-x={Math.PI / 2} material={wallMat}>
        <planeGeometry args={[width, depth + stageDepth]} />
      </mesh>
      {/* acoustic panels + vertical light strips */}
      <instancedMesh ref={panelRef} args={[undefined, wallMat, panelCount]}>
        <boxGeometry args={[0.1, height * 0.62, 1.6]} />
      </instancedMesh>
      <instancedMesh ref={sconceRef} args={[undefined, washMat, panelCount]}>
        <boxGeometry args={[0.02, height * 0.5, 0.05]} />
      </instancedMesh>
      {/* long cove strips near the ceiling */}
      {[-1, 1].map((side) => (
        <mesh key={side} position={[side * (half - 0.11), height - 0.35, (depth - stageDepth) / 2]} material={washMat}>
          <boxGeometry args={[0.03, 0.05, depth + stageDepth - 0.4]} />
        </mesh>
      ))}
      {/* projection booth window */}
      <mesh position={[0, height - 1.1, depth - 0.11]} rotation-y={Math.PI} material={boothMat}>
        <planeGeometry args={[1.4, 0.45]} />
      </mesh>
    </group>
  );
}
