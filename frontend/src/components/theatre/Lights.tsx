"use client";

import { useFrame, useThree } from "@react-three/fiber";
import { useEffect, useRef } from "react";
import { AmbientLight, Color, DirectionalLight, FogExp2, HemisphereLight, PointLight, SpotLight } from "three";
import { useThemeState } from "./context";
import type { Bounds } from "./geometry";

/** All theme-driven lighting + fog + background, eased every frame. */
export default function Lights({ bounds, reduceMotion }: { bounds: Bounds; reduceMotion: boolean }) {
  const theme = useThemeState();
  const scene = useThree((s) => s.scene);
  const amb = useRef<AmbientLight>(null);
  const hemi = useRef<HemisphereLight>(null);
  const key = useRef<DirectionalLight>(null);
  const rimL = useRef<PointLight>(null);
  const rimR = useRef<PointLight>(null);
  const glow = useRef<SpotLight>(null);
  const { width, depth, height, screenCenter } = bounds;

  useEffect(() => {
    scene.fog = new FogExp2(theme.c.fog.getHex(), theme.n.fogDensity);
    scene.background = new Color(theme.c.background);
    return () => {
      scene.fog = null;
      scene.background = null;
    };
  }, [scene, theme]);

  useEffect(() => {
    if (glow.current) {
      glow.current.target.position.set(0, 0.5, depth * 0.6);
      glow.current.target.updateMatrixWorld();
    }
  }, [depth]);

  useFrame((state) => {
    const t = state.clock.elapsedTime;
    const pulse = reduceMotion ? 1 : 1 + theme.n.pulse * 0.4 * Math.sin(t * theme.n.pulseSpeed * Math.PI * 2);
    const c = theme.c;
    if (amb.current) {
      amb.current.color.copy(c.ambient);
      amb.current.intensity = theme.n.ambientI * 0.9;
    }
    if (hemi.current) {
      hemi.current.color.copy(c.key);
      hemi.current.groundColor.copy(c.secondary);
      hemi.current.intensity = theme.n.ambientI * 0.8;
    }
    if (key.current) {
      key.current.color.copy(c.key);
      key.current.intensity = theme.n.keyI;
    }
    for (const r of [rimL.current, rimR.current]) {
      if (!r) continue;
      r.color.copy(c.wallWash);
      r.intensity = theme.n.rimI * 18 * pulse;
    }
    if (glow.current) {
      glow.current.color.copy(c.screenGlow);
      glow.current.intensity = theme.n.screenI * 40;
    }
    const fog = scene.fog as FogExp2 | null;
    if (fog) {
      fog.color.copy(c.fog);
      fog.density = theme.n.fogDensity;
    }
    (scene.background as Color | null)?.copy(c.background);
  });

  return (
    <>
      <ambientLight ref={amb} />
      <hemisphereLight ref={hemi} />
      <directionalLight ref={key} position={[0, height * 1.4, depth * 1.1]} />
      <pointLight ref={rimL} position={[-width / 2 + 0.8, height * 0.7, depth * 0.45]} distance={depth * 1.2} decay={1.4} />
      <pointLight ref={rimR} position={[width / 2 - 0.8, height * 0.7, depth * 0.45]} distance={depth * 1.2} decay={1.4} />
      <spotLight ref={glow} position={[screenCenter[0], screenCenter[1], 0.6]} angle={1.1} penumbra={1} distance={depth * 1.5} decay={1.2} />
    </>
  );
}
