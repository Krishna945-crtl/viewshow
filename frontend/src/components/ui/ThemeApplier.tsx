"use client";

import { useEffect } from "react";
import { applyThemeToDocument, DEFAULT_THEME } from "@/lib/theme";
import type { Theme } from "@/lib/types";

/** Drop on any page to tint the whole UI with a movie's theme. */
export default function ThemeApplier({ theme }: { theme?: Theme | null }) {
  useEffect(() => {
    applyThemeToDocument(theme ?? DEFAULT_THEME);
  }, [theme]);
  return null;
}
