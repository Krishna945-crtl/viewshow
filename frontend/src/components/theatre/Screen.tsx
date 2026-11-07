"use client";

import { useFrame } from "@react-three/fiber";
import { useMemo } from "react";
import { MeshBasicMaterial, PlaneGeometry, ShaderMaterial } from "three";
import { usePrefs } from "@/lib/prefs";
import type { Screen as ScreenSpec } from "@/lib/types";
import { useThemeState } from "./context";

/** Curved screen with a slow, original "idle loop" built from the theme gradient. */
export default function Screen({ spec }: { spec: ScreenSpec }) {
  const theme = useThemeState();
  const reduce = usePrefs((p) => p.reduceMotion);
  const { width: w, height: h, curvature, bottom } = spec;

  const geo = useMemo(() => {
    const g = new PlaneGeometry(w, h, 48, 1);
    const pos = g.attributes.position;
    for (let i = 0; i < pos.count; i++) {
      const nx = pos.getX(i) / (w / 2);
      pos.setZ(i, curvature * w * 0.12 * nx * nx); // edges wrap towards the audience
    }
    g.computeVertexNormals();
    return g;
  }, [w, h, curvature]);

  const frameGeo = useMemo(() => {
    const g = geo.clone();
    g.scale((w + 0.5) / w, (h + 0.4) / h, 1);
    g.translate(0, 0, -0.03);
    return g;
  }, [geo, w, h]);

  const mat = useMemo(
    () =>
      new ShaderMaterial({
        toneMapped: false,
        uniforms: {
          uTime: { value: 0 }, uI: { value: 1 },
          c0: { value: theme.c.grad0 }, c1: { value: theme.c.grad1 }, c2: { value: theme.c.grad2 },
        },
        vertexShader: `varying vec2 vUv; void main(){ vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position,1.0); }`,
        fragmentShader: /* glsl */ `
          uniform float uTime; uniform float uI; uniform vec3 c0; uniform vec3 c1; uniform vec3 c2;
          varying vec2 vUv;
          float blob(vec2 p, vec2 c, float r){ return smoothstep(r, 0.0, length(p - c)); }
          void main(){
            vec2 p = vUv * vec2(2.2, 1.0);
            float t = uTime * 0.08;
            vec3 col = mix(c0, c1, smoothstep(0.0, 1.1, vUv.y + 0.15 * sin(vUv.x * 3.0 + t * 2.0)));
            col += c2 * 0.55 * blob(p, vec2(1.1 + 0.7 * sin(t * 1.3), 0.55 + 0.2 * cos(t)), 0.65);
            col += c1 * 0.35 * blob(p, vec2(0.6 + 0.5 * cos(t * 0.9), 0.35), 0.5);
            float vig = smoothstep(0.85, 0.25, length(vUv - 0.5));
            gl_FragColor = vec4(col * (0.35 + 0.75 * vig) * uI, 1.0);
          }
        `,
      }),
    // colour uniforms hold references to the live, lerping colours
    [theme],
  );
  const frameMat = useMemo(() => new MeshBasicMaterial({ color: "#020203" }), []);

  useFrame((_, dt) => {
    if (!reduce) mat.uniforms.uTime.value += dt;
    mat.uniforms.uI.value = 0.55 + theme.n.screenI * 0.5;
  });

  return (
    <group position={[0, bottom + h / 2, 0]}>
      <mesh geometry={frameGeo} material={frameMat} />
      <mesh geometry={geo} material={mat} />
    </group>
  );
}
