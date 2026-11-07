import { CanvasTexture, LinearFilter, LinearMipmapLinearFilter, ShaderMaterial } from "three";

const GRID = 10; // 10x10 -> seat numbers 1..100

let atlas: CanvasTexture | null = null;

export function numberAtlas() {
  if (atlas) return atlas;
  const size = 1024;
  const cell = size / GRID;
  const c = document.createElement("canvas");
  c.width = c.height = size;
  const g = c.getContext("2d")!;
  g.fillStyle = "#fff";
  g.textAlign = "center";
  g.textBaseline = "middle";
  g.font = `700 ${cell * 0.56}px ui-sans-serif, system-ui, sans-serif`;
  for (let i = 0; i < GRID * GRID; i++) {
    const cx = (i % GRID) * cell + cell / 2;
    const cy = Math.floor(i / GRID) * cell + cell / 2 + cell * 0.03;
    g.fillText(String(i + 1), cx, cy);
  }
  atlas = new CanvasTexture(c);
  // mipmaps keep far-away numbers legible ("1" was aliasing into "!" at the back of big halls)
  atlas.minFilter = LinearMipmapLinearFilter;
  atlas.magFilter = LinearFilter;
  atlas.anisotropy = 4;
  atlas.flipY = false;
  return atlas;
}

/**
 * Unlit, fog-free plate: status colour + seat number from an atlas.
 * Because it ignores scene lights, the status stays readable under any theme.
 */
export function plateMaterial() {
  return new ShaderMaterial({
    uniforms: { uAtlas: { value: numberAtlas() }, uTime: { value: 0 } },
    vertexShader: /* glsl */ `
      attribute float aNum;
      attribute vec3 aColor;
      attribute vec3 aInk;
      attribute float aGlow;
      varying vec2 vUv;
      varying vec3 vColor;
      varying vec3 vInk;
      varying float vGlow;
      varying float vNum;
      void main() {
        vUv = uv;
        vColor = aColor; vInk = aInk; vGlow = aGlow; vNum = aNum;
        vec3 p = position * (1.0 + aGlow * 0.35);
        gl_Position = projectionMatrix * modelViewMatrix * instanceMatrix * vec4(p, 1.0);
      }
    `,
    fragmentShader: /* glsl */ `
      uniform sampler2D uAtlas;
      uniform float uTime;
      varying vec2 vUv;
      varying vec3 vColor;
      varying vec3 vInk;
      varying float vGlow;
      varying float vNum;
      float rbox(vec2 p, vec2 b, float r) { vec2 q = abs(p) - b + r; return length(max(q, 0.0)) + min(max(q.x, q.y), 0.0) - r; }
      void main() {
        vec2 p = vUv - 0.5;
        float d = rbox(p * vec2(1.0, 0.56), vec2(0.47, 0.25), 0.1);
        if (d > 0.0) discard;
        // varyings arrive as 10.99999 instead of 11.0 - snap to a whole index first,
        // otherwise seats 1, 11, 21... read from the wrong atlas cell
        float idx = floor(vNum - 0.5);
        vec2 cell = vec2(mod(idx, ${GRID}.0), floor((idx + 0.5) / ${GRID}.0));
        vec2 local = vec2(vUv.x - 0.5, 0.5 - vUv.y) * vec2(1.25, 0.7);
        vec2 uv = (cell + vec2(0.5) + local) / ${GRID}.0;
        float ink = texture2D(uAtlas, vec2(uv.x, uv.y)).a;
        vec3 col = mix(vColor, vInk, ink);
        float ring = smoothstep(-0.05, -0.02, d) * vGlow;
        col = mix(col, vec3(1.0), ring * (0.6 + 0.4 * sin(uTime * 6.0)));
        gl_FragColor = vec4(col, 1.0);
      }
    `,
  });
}
