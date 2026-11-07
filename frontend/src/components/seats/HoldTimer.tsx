"use client";

import { useEffect, useState } from "react";

export default function HoldTimer({ deadline, onExpire }: { deadline: number | null; onExpire: () => void }) {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    if (!deadline) return;
    const t = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(t);
  }, [deadline]);
  const left = deadline ? Math.max(0, Math.floor((deadline - now) / 1000)) : 0;
  useEffect(() => {
    if (deadline && left === 0) onExpire();
  }, [left, deadline, onExpire]);
  if (!deadline) return null;
  const urgent = left < 60;
  return (
    <span className={`text-xs tabular-nums rounded-full px-2.5 py-1 border ${urgent ? "border-red-400/60 text-red-300" : "border-line text-muted"}`}
          role="timer" aria-live={urgent ? "assertive" : "off"} aria-label={`Seats held for ${Math.floor(left / 60)} minutes ${left % 60} seconds`}>
      ⏱ {String(Math.floor(left / 60)).padStart(2, "0")}:{String(left % 60).padStart(2, "0")}
    </span>
  );
}
