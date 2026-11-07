"use client";

import { create } from "zustand";
import { load, save } from "./storage";
import type { User } from "./types";

interface Session { access: string; refresh: string; user: User }

interface AuthState {
  session: Session | null;
  ready: boolean;
  init: () => void;
  setSession: (s: Session | null) => void;
}

export const useAuth = create<AuthState>((set) => ({
  session: null,
  ready: false,
  init: () => set({ session: load<Session | null>("cv.session", null), ready: true }),
  setSession: (session) => {
    save("cv.session", session);
    set({ session });
  },
}));

export const currentToken = () => useAuth.getState().session?.access ?? null;
