"use client";

import { AnimatePresence, motion } from "framer-motion";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { usePrefs } from "@/lib/prefs";

const SLIDES = [
  { title: "Walk into the theatre", body: "Explore a real-scale 3D auditorium before you book. Orbit, zoom and fly between sections." },
  { title: "Sit before you pay", body: "View From My Seat drops you to eye level so you know exactly how the screen will look." },
  { title: "Every film has a mood", body: "The hall re-lights itself for each movie — desert gold, abyssal blue, neon noir and more." },
];

export default function Splash() {
  const router = useRouter();
  const { onboarded, hydrated, set } = usePrefs();
  const [i, setI] = useState(0);

  useEffect(() => {
    if (hydrated && onboarded) router.replace("/home/");
  }, [hydrated, onboarded, router]);

  const done = () => {
    set({ onboarded: true });
    router.push("/home/");
  };

  if (!hydrated || onboarded) {
    return (
      <div className="min-h-dvh grid place-items-center">
        <motion.div initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }} className="text-3xl font-bold">
          CineVerse<span className="text-accent">3D</span>
        </motion.div>
      </div>
    );
  }

  return (
    <div className="min-h-dvh flex flex-col px-6 pt-[max(env(safe-area-inset-top),2rem)] pb-10 max-w-md mx-auto">
      <div className="flex justify-between items-center">
        <span className="font-bold text-lg">CineVerse<span className="text-accent">3D</span></span>
        <button className="text-sm text-muted" onClick={done}>Skip</button>
      </div>
      <div className="flex-1 grid place-items-center">
        <div className="w-full">
          <div className="relative mx-auto mb-10 aspect-square w-64">
            <div className="absolute inset-0 rounded-full bg-primary/30 blur-3xl animate-pulse" />
            <svg viewBox="0 0 200 200" className="relative" aria-hidden>
              <path d="M30 60 Q100 35 170 60 L165 100 Q100 80 35 100Z" fill="var(--cv-accent)" opacity="0.85" />
              {Array.from({ length: 5 }).map((_, r) =>
                Array.from({ length: 7 + r }).map((__, c) => (
                  <rect key={`${r}-${c}`} x={100 - ((7 + r) * 14) / 2 + c * 14 + 2} y={118 + r * 14} width="10" height="9" rx="2"
                        fill={r === 2 && c === 4 ? "#22c55e" : "var(--cv-primary)"} opacity={0.5 + r * 0.1} />
                )),
              )}
            </svg>
          </div>
          <AnimatePresence mode="wait">
            <motion.div key={i} initial={{ opacity: 0, x: 30 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -30 }}>
              <h1 className="text-3xl font-bold leading-tight">{SLIDES[i].title}</h1>
              <p className="mt-3 text-muted">{SLIDES[i].body}</p>
            </motion.div>
          </AnimatePresence>
        </div>
      </div>
      <div className="flex items-center justify-between">
        <div className="flex gap-1.5" aria-label={`Step ${i + 1} of ${SLIDES.length}`}>
          {SLIDES.map((_, k) => (
            <span key={k} className={`h-1.5 rounded-full transition-all ${k === i ? "w-6 bg-accent" : "w-1.5 bg-white/25"}`} />
          ))}
        </div>
        <button className="btn btn-primary" onClick={() => (i < SLIDES.length - 1 ? setI(i + 1) : done())}>
          {i < SLIDES.length - 1 ? "Next" : "Start exploring"}
        </button>
      </div>
    </div>
  );
}
