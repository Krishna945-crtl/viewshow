export type GpuTier = "none" | "low" | "high";

let cached: GpuTier | null = null;

/** Rough capability check: can we do WebGL at all, and is this a beefy device? */
export function detectGpu(): GpuTier {
  if (cached) return cached;
  if (typeof window === "undefined") return "none";
  try {
    const c = document.createElement("canvas");
    const gl = (c.getContext("webgl2") || c.getContext("webgl")) as WebGLRenderingContext | null;
    if (!gl) return (cached = "none");
    const mobile = /Android|iPhone|iPad|iPod|Mobile/i.test(navigator.userAgent);
    const cores = navigator.hardwareConcurrency || 4;
    const mem = (navigator as Navigator & { deviceMemory?: number }).deviceMemory ?? 4;
    const dbg = gl.getExtension("WEBGL_debug_renderer_info");
    const renderer = dbg ? String(gl.getParameter(dbg.UNMASKED_RENDERER_WEBGL)) : "";
    const software = /SwiftShader|llvmpipe|Software/i.test(renderer);
    gl.getExtension("WEBGL_lose_context")?.loseContext();
    if (software || cores <= 4 || mem <= 2 || (mobile && cores <= 6)) return (cached = "low");
    return (cached = "high");
  } catch {
    return (cached = "none");
  }
}
