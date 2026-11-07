"use client";

import { useFrame } from "@react-three/fiber";
import { useMemo } from "react";
import { AdditiveBlending, BufferAttribute, BufferGeometry, ShaderMaterial } from "three";
import { useThemeState } from "./context";

const KINDS = ["none", "dust", "sand", "embers", "bubbles", "stars", "snow", "rain", "sparks", "petals", "leaves", "mist"];

/** One Points draw call. Motion is computed entirely in the vertex shader. */
export default function Particles({ count, box }: { count: number; box: [number, number, number] }) {
  const theme = useThemeState();
  const geo = useMemo(() => {
    const g = new BufferGeometry();
    const seed = new Float32Array(count * 4);
    for (let i = 0; i < seed.length; i++) seed[i] = Math.random();
    g.setAttribute("position", new BufferAttribute(new Float32Array(count * 3), 3));
    g.setAttribute("aSeed", new BufferAttribute(seed, 4));
    g.boundingSphere = null;
    return g;
  }, [count]);

  const mat = useMemo(
    () =>
      new ShaderMaterial({
        transparent: true,
        depthWrite: false,
        blending: AdditiveBlending,
        uniforms: {
          uTime: { value: 0 }, uKind: { value: 1 }, uSpeed: { value: 0.5 }, uOpacity: { value: 1 },
          uBox: { value: box }, uColor: { value: theme.c.particle }, uPixel: { value: 1 },
        },
        vertexShader: /* glsl */ `
          attribute vec4 aSeed;
          uniform float uTime; uniform float uKind; uniform float uSpeed; uniform vec3 uBox; uniform float uPixel;
          varying float vAlpha; varying float vKind;
          void main(){
            vec3 b = uBox;
            vec3 p = vec3((aSeed.x - 0.5) * b.x, aSeed.y * b.y, aSeed.z * b.z - 1.0);
            vec3 v = vec3(0.0);
            float size = 3.0; float alpha = 0.55; float t = uTime * uSpeed;
            int k = int(uKind + 0.5);
            if (k == 1) { v = vec3(0.03, 0.015, 0.02); size = 2.5; alpha = 0.35; }
            else if (k == 2) { v = vec3(0.9, -0.05, 0.12); size = 2.2; alpha = 0.6; p.y = aSeed.y * b.y * 0.6; }
            else if (k == 3) { v = vec3(0.04, 0.5, 0.0); size = 3.5; alpha = 0.5 + 0.5 * sin(uTime * 7.0 + aSeed.w * 30.0); }
            else if (k == 4) { v = vec3(0.0, 0.35, 0.0); p.x += 0.15 * sin(uTime * 1.5 + aSeed.w * 20.0); size = 4.5; alpha = 0.45; }
            else if (k == 5) { p.y = b.y * (0.7 + 0.3 * aSeed.y); size = 2.4; alpha = 0.35 + 0.6 * abs(sin(uTime * 1.2 + aSeed.w * 40.0)); }
            else if (k == 6) { v = vec3(0.05, -0.35, 0.0); p.x += 0.3 * sin(uTime * 0.8 + aSeed.w * 10.0); size = 4.0; alpha = 0.7; }
            else if (k == 7) { v = vec3(0.0, -6.0, 0.0); size = 5.0; alpha = 0.35; }
            else if (k == 8) { v = vec3(0.0, 1.2, 0.0); size = 2.6; alpha = 0.4 + 0.6 * step(0.6, fract(uTime * 2.0 + aSeed.w)); }
            else if (k == 9 || k == 10) { v = vec3(0.25, -0.28, 0.05); p.x += 0.5 * sin(uTime + aSeed.w * 6.0); size = 5.0; alpha = 0.6; }
            else if (k == 11) { v = vec3(0.08, 0.0, 0.03); p.y = aSeed.y * 1.6; size = 26.0; alpha = 0.08; }
            p += v * t * (0.6 + aSeed.w * 0.8);
            p.x = mod(p.x + b.x * 0.5, b.x) - b.x * 0.5;
            p.y = mod(p.y, b.y);
            p.z = mod(p.z + 1.0, b.z) - 1.0;
            vec4 mv = modelViewMatrix * vec4(p, 1.0);
            gl_Position = projectionMatrix * mv;
            gl_PointSize = size * uPixel * (8.0 / -mv.z);
            vAlpha = alpha; vKind = uKind;
          }
        `,
        fragmentShader: /* glsl */ `
          uniform vec3 uColor; uniform float uOpacity;
          varying float vAlpha; varying float vKind;
          void main(){
            vec2 c = gl_PointCoord - 0.5;
            float d = length(c);
            if (int(vKind + 0.5) == 7) d = abs(c.x) * 4.0; // rain = thin streak
            float a = smoothstep(0.5, 0.0, d) * vAlpha * uOpacity;
            if (a < 0.01) discard;
            gl_FragColor = vec4(uColor, a);
          }
        `,
      }),
    [theme, box],
  );

  useFrame((state, dt) => {
    const u = mat.uniforms;
    u.uTime.value += dt;
    u.uKind.value = Math.max(0, KINDS.indexOf(theme.particleKind));
    u.uSpeed.value = 0.25 + theme.n.pSpeed;
    u.uOpacity.value = theme.particleFade * Math.min(1, theme.n.pDensity * 1.6);
    u.uPixel.value = state.gl.getPixelRatio();
  });

  return <points geometry={geo} material={mat} frustumCulled={false} />;
}
