"use client";

import { AdaptiveDpr, PerformanceMonitor } from "@react-three/drei";
import { Canvas, useFrame } from "@react-three/fiber";
import { useEffect, useMemo, useRef, useState } from "react";
import { ACESFilmicToneMapping } from "three";
import { usePrefs } from "@/lib/prefs";
import type { Seat, SeatMap, Theme } from "@/lib/types";
import { detectGpu } from "@/lib/webgl";
import CameraRig from "./CameraRig";
import { ThemeCtx } from "./context";
import { roomBounds } from "./geometry";
import Lights from "./Lights";
import Particles from "./Particles";
import Room from "./Room";
import Screen from "./Screen";
import Seats from "./Seats";
import { ThemeState } from "./themeState";

function ThemeDriver({ state }: { state: ThemeState }) {
  useFrame((_, dt) => state.update(dt));
  return null;
}

interface Props {
  map: SeatMap;
  theme: Theme;
  interactive?: boolean;
  onSeatClick?: (s: Seat) => void;
  onSlow?: () => void;
  className?: string;
}

export default function Auditorium3D({ map, theme, interactive = true, onSeatClick, onSlow, className }: Props) {
  const reduceMotion = usePrefs((p) => p.reduceMotion);
  const qualityPref = usePrefs((p) => p.quality);
  const tier = useMemo(() => detectGpu(), []);
  const low = qualityPref === "low" || (qualityPref === "auto" && tier === "low");
  const maxDpr = low ? 1 : Math.min(2, typeof window !== "undefined" ? window.devicePixelRatio : 1);
  const [dpr, setDpr] = useState(maxDpr);

  const themeState = useMemo(() => new ThemeState(theme), []); // eslint-disable-line react-hooks/exhaustive-deps
  const first = useRef(true);
  useEffect(() => {
    themeState.setTarget(theme, first.current || reduceMotion);
    first.current = false;
  }, [theme, themeState, reduceMotion]);

  const bounds = useMemo(() => roomBounds(map), [map]);
  const particleCount = reduceMotion ? 0 : low ? 260 : 700;

  return (
    <div className={className} style={{ touchAction: "none" }}>
      <Canvas
        dpr={dpr}
        gl={{ antialias: !low, powerPreference: "high-performance", toneMapping: ACESFilmicToneMapping }}
        camera={{ fov: 50, near: 0.05, far: 200, position: [0, 12, bounds.maxZ + 6] }}
        aria-label="Interactive 3D auditorium"
        role="img"
      >
        <ThemeCtx.Provider value={themeState}>
          <ThemeDriver state={themeState} />
          <PerformanceMonitor
            onIncline={() => setDpr(maxDpr)}
            onDecline={() => setDpr(Math.max(0.75, maxDpr * 0.6))}
            flipflops={3}
            onFallback={() => {
              setDpr(0.75);
              onSlow?.();
            }}
          />
          <AdaptiveDpr pixelated />
          <Lights bounds={bounds} reduceMotion={reduceMotion} />
          <Room seats={map.seats} bounds={bounds} />
          <Screen spec={map.auditorium.screen} />
          <Seats seats={map.seats} interactive={interactive} onSeatClick={onSeatClick} />
          {particleCount > 0 && (
            <Particles count={particleCount} box={[bounds.width - 0.6, bounds.height - 0.2, bounds.depth + 1]} />
          )}
          <CameraRig seats={map.seats} bounds={bounds} reduceMotion={reduceMotion} />
        </ThemeCtx.Provider>
      </Canvas>
    </div>
  );
}
