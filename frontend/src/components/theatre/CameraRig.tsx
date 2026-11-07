"use client";

import { CameraControls } from "@react-three/drei";
import { useThree } from "@react-three/fiber";
import { useEffect, useRef } from "react";
import { PerspectiveCamera, Vector3 } from "three";
import type { Seat } from "@/lib/types";
import { useCam } from "./camera";
import { Bounds, EYE_HEIGHT } from "./geometry";

const LOOK = 0.25; // first-person: orbit radius around the eye

export default function CameraRig({ seats, bounds, reduceMotion }: { seats: Seat[]; bounds: Bounds; reduceMotion: boolean }) {
  const ref = useRef<CameraControls>(null);
  const camera = useThree((s) => s.camera) as PerspectiveCamera;
  const size = useThree((s) => s.size);
  const { view, seatId, nonce } = useCam();
  const { width, depth, height, maxZ, maxY, screenCenter } = bounds;
  const portrait = size.height > size.width;

  useEffect(() => {
    const c = ref.current;
    if (!c) return;
    const smooth = !reduceMotion;
    const [sx, sy, sz] = screenCenter;
    const back = portrait ? 1.35 : 1; // phones need to stand further back to fit the room

    const free = () => {
      c.minDistance = 1.5;
      c.maxDistance = depth * 1.2;
      c.minPolarAngle = 0.15;
      c.maxPolarAngle = Math.PI * 0.53;
      c.minAzimuthAngle = -Infinity;
      c.maxAzimuthAngle = Infinity;
      c.truckSpeed = 1;
      c.dollySpeed = 1;
      camera.fov = portrait ? 68 : 55;
    };

    if (view === "seat" && seatId) {
      const s = seats.find((x) => x.id === seatId);
      if (!s) return;
      const eye = new Vector3(s.x, s.y + EYE_HEIGHT, s.z);
      const dir = new Vector3(sx, sy, sz).sub(eye).normalize();
      const tgt = eye.clone().addScaledVector(dir, LOOK);
      c.minDistance = c.maxDistance = LOOK;
      c.truckSpeed = 0;
      c.dollySpeed = 0;
      // look around, but not behind you
      const az = Math.atan2(eye.x - tgt.x, eye.z - tgt.z);
      c.minAzimuthAngle = az - 1.2;
      c.maxAzimuthAngle = az + 1.2;
      c.minPolarAngle = 0.6;
      c.maxPolarAngle = 2.2;
      camera.fov = 58; // roughly what you'd perceive sitting down
      camera.updateProjectionMatrix();
      c.setLookAt(eye.x, eye.y, eye.z, tgt.x, tgt.y, tgt.z, smooth);
      return;
    }

    free();
    camera.updateProjectionMatrix();
    const poses: Record<string, [number, number, number, number, number, number]> = {
      // stay inside the room: up near the ceiling at the back wall, looking down over the seats
      overview: [0, height - 0.7, depth - 0.5, 0, sy * 0.35, maxZ * 0.3 / back],
      stage: [0, sy * 0.7, 1.2, 0, maxY * 0.6 + 0.8, maxZ * 0.6],
      back: [0, maxY + EYE_HEIGHT + 0.25, maxZ + 0.6, sx, sy, sz],
      side: [width / 2 - 1.0, height * 0.72, maxZ * 0.82, -width * 0.08, sy * 0.5, maxZ * 0.3],
    };
    const p = poses[view] ?? poses.overview;
    c.setLookAt(...p, smooth);
  }, [view, seatId, nonce, seats, width, depth, height, maxZ, maxY, screenCenter, camera, reduceMotion, portrait]);

  return <CameraControls ref={ref} makeDefault smoothTime={reduceMotion ? 0 : 0.6} draggingSmoothTime={0.12} />;
}
