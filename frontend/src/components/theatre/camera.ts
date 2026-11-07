"use client";

import { create } from "zustand";

export type CamView = "overview" | "stage" | "back" | "side" | "seat";

interface CamStore {
  view: CamView;
  seatId: string | null;
  nonce: number;
  go: (view: CamView, seatId?: string | null) => void;
}

export const useCam = create<CamStore>((set, get) => ({
  view: "overview",
  seatId: null,
  nonce: 0,
  go: (view, seatId = null) => set({ view, seatId, nonce: get().nonce + 1 }),
}));
