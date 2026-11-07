import { createContext, useContext } from "react";
import type { ThemeState } from "./themeState";

export const ThemeCtx = createContext<ThemeState | null>(null);

export function useThemeState() {
  const t = useContext(ThemeCtx);
  if (!t) throw new Error("ThemeCtx missing");
  return t;
}
