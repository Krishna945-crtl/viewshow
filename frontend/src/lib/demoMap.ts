"use client";

import { useEffect, useState } from "react";
import { api } from "./api";
import { useSeats } from "./seats";
import type { Movie, SeatMap, ShowSummary } from "./types";

/** Any real auditorium, for previews (Theme Lab, admin theme editor). */
export function useDemoMap() {
  const [map, setMap] = useState<SeatMap | null>(null);
  useEffect(() => {
    let dead = false;
    (async () => {
      const movies = await api<Movie[]>("/movies");
      for (const m of movies) {
        const st = await api<{ theatres: { shows: ShowSummary[] }[] }>(`/movies/${m.slug}/showtimes`);
        const all = st.theatres.flatMap((t) => t.shows);
        const pick = all.find((s) => s.auditorium.name.includes("Grand")) ?? all[0];
        if (!pick) continue;
        const sm = await api<SeatMap>(`/shows/${pick.id}/seats`);
        if (dead) return;
        useSeats.setState({ map: sm, states: Object.fromEntries(sm.seats.map((s) => [s.id, { state: s.state, tag: s.tag }])) });
        setMap(sm);
        return;
      }
    })().catch(() => {});
    return () => {
      dead = true;
    };
  }, []);
  return map;
}
