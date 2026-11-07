"use client";

import { AnimatePresence, motion } from "framer-motion";
import { create } from "zustand";

interface Toast { id: number; text: string; kind: "info" | "error" | "success" }
const useToasts = create<{ list: Toast[] }>(() => ({ list: [] }));
let n = 0;

export function toast(text: string, kind: Toast["kind"] = "info") {
  const id = ++n;
  useToasts.setState((s) => ({ list: [...s.list.slice(-2), { id, text, kind }] }));
  setTimeout(() => useToasts.setState((s) => ({ list: s.list.filter((t) => t.id !== id) })), 4200);
}

export function Toaster() {
  const list = useToasts((s) => s.list);
  return (
    <div className="fixed z-50 left-1/2 -translate-x-1/2 bottom-24 sm:bottom-6 flex flex-col gap-2 w-[min(92vw,420px)]"
         role="status" aria-live="polite">
      <AnimatePresence>
        {list.map((t) => (
          <motion.div key={t.id} initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: 8 }}
            className={`glass rounded-2xl px-4 py-3 text-sm shadow-2xl ${t.kind === "error" ? "border-red-500/50" : t.kind === "success" ? "border-green-500/50" : ""}`}>
            {t.text}
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
}
