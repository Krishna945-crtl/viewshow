import { BoxGeometry, BufferGeometry, CylinderGeometry } from "three";
import { mergeGeometries } from "three/examples/jsm/utils/BufferGeometryUtils.js";
import type { SeatCategory } from "@/lib/types";

// metres, mirrors backend SEAT_SPECS
export const SEAT_WIDTH: Record<SeatCategory, number> = { standard: 0.56, premium: 0.62, vip: 0.78, recliner: 0.9 };

type Part = [w: number, h: number, d: number, x: number, y: number, z: number, tiltX?: number];

function box([w, h, d, x, y, z, tilt = 0]: Part) {
  const g = new BoxGeometry(w, h, d, 1, 1, 1);
  if (tilt) g.rotateX(tilt);
  g.translate(x, y, z);
  return g;
}

/** Low-poly seat model, origin at floor centre, facing -z (towards the screen). */
export function seatGeometry(cat: SeatCategory): BufferGeometry {
  const w = SEAT_WIDTH[cat] - 0.05;
  const inner = w - 0.12;
  const arm = cat === "recliner" ? 0.12 : 0.06;
  const parts: Part[] = [];
  if (cat === "recliner") {
    parts.push(
      [inner, 0.2, 0.62, 0, 0.42, -0.02], // thick cushion
      [inner, 0.82, 0.2, 0, 0.88, 0.3, 0.22], // reclined back
      [arm, 0.3, 0.8, w / 2 - arm / 2, 0.55, 0.02],
      [arm, 0.3, 0.8, -w / 2 + arm / 2, 0.55, 0.02],
      [inner, 0.11, 0.36, 0, 0.3, -0.48, -0.25], // footrest
      [w - 0.06, 0.32, 0.7, 0, 0.16, 0.02], // base
    );
  } else {
    const back = cat === "standard" ? 0.6 : 0.68;
    parts.push(
      [inner, 0.11, 0.48, 0, 0.46, -0.03],
      [inner, back, 0.09, 0, 0.5 + back / 2, 0.24, 0.12],
      [arm, 0.07, 0.48, w / 2 - arm / 2, 0.66, 0],
      [arm, 0.07, 0.48, -w / 2 + arm / 2, 0.66, 0],
      [arm, 0.62, 0.08, w / 2 - arm / 2, 0.33, 0.12],
      [arm, 0.62, 0.08, -w / 2 + arm / 2, 0.33, 0.12],
      [inner * 0.5, 0.42, 0.24, 0, 0.21, 0.06],
    );
    if (cat !== "standard") parts.push([inner * 0.6, 0.16, 0.1, 0, 0.5 + back + 0.06, 0.29, 0.12]); // headrest
  }
  const geos: BufferGeometry[] = parts.map(box);
  if (cat === "vip") {
    // little cup holder puck on the right arm - reads as "premium" at a glance
    const cup = new CylinderGeometry(0.035, 0.035, 0.04, 10);
    cup.translate(w / 2 - arm / 2, 0.715, -0.15);
    geos.push(cup);
  }
  const merged = mergeGeometries(geos.map((g) => (g.index ? g.toNonIndexed() : g)), false)!;
  merged.computeVertexNormals();
  geos.forEach((g) => g.dispose());
  return merged;
}

/** Where the number plate sits on top of the backrest. */
export function platePose(cat: SeatCategory) {
  if (cat === "recliner") return { y: 1.32, z: 0.42 };
  const back = cat === "standard" ? 0.6 : 0.68;
  return { y: 0.5 + back + (cat === "standard" ? 0.05 : 0.17), z: 0.33 };
}
