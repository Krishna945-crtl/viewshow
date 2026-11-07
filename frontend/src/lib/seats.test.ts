import { describe, expect, it } from "vitest";
import { displayState, selectedIds } from "./seats";
import type { SeatMap } from "./types";

const map = { my_tag: "me" } as SeatMap;
const states = {
  a: { state: "available" as const, tag: null },
  b: { state: "held" as const, tag: "me" },
  c: { state: "held" as const, tag: "someone" },
  d: { state: "booked" as const, tag: null },
};

describe("seat display state", () => {
  it("distinguishes my holds from other people's", () => {
    const s = { map, states, pending: {} };
    expect(displayState(s, "a")).toBe("available");
    expect(displayState(s, "b")).toBe("selected");
    expect(displayState(s, "c")).toBe("held");
    expect(displayState(s, "d")).toBe("booked");
    expect(displayState(s, "zzz")).toBe("blocked");
  });

  it("pending wins while a request is in flight", () => {
    expect(displayState({ map, states, pending: { a: true } }, "a")).toBe("pending");
  });

  it("selectedIds only returns my holds", () => {
    expect(selectedIds({ map, states })).toEqual(["b"]);
    expect(selectedIds({ map: { ...map, my_tag: null }, states })).toEqual([]);
  });
});
