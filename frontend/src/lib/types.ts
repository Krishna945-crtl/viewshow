export type SeatState = "available" | "held" | "booked" | "blocked";
export type SeatCategory = "standard" | "premium" | "recliner" | "vip";

export interface Theme {
  name: string;
  source: "auto" | "custom";
  archetypes: string[];
  mood: string;
  palette: { primary: string; secondary: string; accent: string; background: string; surface: string };
  lighting: {
    ambient_color: string; ambient_intensity: number; key_color: string; key_intensity: number;
    rim_color: string; rim_intensity: number; wall_wash: string; floor_glow: string;
  };
  fog: { color: string; density: number };
  screen: { glow_color: string; glow_intensity: number; idle_gradient: string[] };
  particles: { kind: string; density: number; color: string; speed: number };
  animation: { light_pulse: number; pulse_speed: number; transition_ms: number };
  sound: { preset: string; default_volume: number };
  seat_fabric: string;
  explain?: ThemeExplain;
}

export interface Swatch { hex: string; weight: number }

export interface ThemeExplain {
  confidence: number;
  palette_from: "archetypes" | "poster colours" | "admin colours" | "title signature";
  signature_shift_deg: number;
  signals: { archetype: string; label: string; score: number; evidence: string[] }[];
}

export interface Movie {
  id: string; slug: string; title: string; tagline: string | null; genres: string[];
  language: string; certificate: string; runtime_minutes: number; rating: number | null;
  release_date: string | null; poster_url: string | null; backdrop_url: string | null;
  is_active: boolean; theme: Theme; theme_id: string | null;
  synopsis?: string; cast?: string[]; trailer_url?: string | null; mood_tags?: string[]; palette_hint?: string[];
  keywords?: string[]; art_palette?: Swatch[]; tmdb_id?: number | null;
}

export interface TmdbHit {
  tmdb_id: number; title: string; year: number | null; language: string; overview: string;
  rating: number | null; poster_thumb: string | null; imported_id: string | null;
}

export interface User { id: string; email: string; full_name: string; city: string | null; is_admin: boolean }

export interface ShowSummary {
  id: string; movie_id: string; starts_at: string; format: string; language: string; is_cancelled: boolean;
  auditorium: { id: string; name: string; theatre_id: string }; prices: Record<string, number>;
}

export interface TheatreInfo {
  id: string; name: string; city: string; address: string; is_demo: boolean; amenities?: string[];
}

export interface ShowDetail extends ShowSummary { movie: Movie; theatre: TheatreInfo }

export interface ViewInfo { score: number; verdict: string; fov: number; off_axis: number; vertical: number; distance: number }

export interface Seat {
  id: string; label: string; row: string; number: number; category: SeatCategory; block: number;
  x: number; y: number; z: number; yaw: number; col: number; grid_row: number; accessible: boolean;
  price_paise: number; state: SeatState; tag: string | null; view: ViewInfo;
}

export interface Screen { width: number; height: number; curvature: number; distance: number; bottom: number }

export interface SeatMap {
  show_id: string;
  auditorium: {
    id: string; name: string; dimensions_verified: boolean; screen: Screen; aisle_width: number;
    seat_count: number; rows: number; by_category: Record<string, number>;
    room: { width: number; depth: number; height: number };
  };
  prices: Record<string, number>; my_tag: string | null; hold_deadline_ms: number | null; seats: Seat[];
}

export interface Booking {
  id: string; reference: string; status: "PENDING_PAYMENT" | "CONFIRMED" | "CANCELLED" | "EXPIRED" | "FAILED";
  amount_paise: number; convenience_fee_paise: number; expires_at: string; confirmed_at: string | null;
  created_at: string; checked_in_at: string | null;
  seats: { id: string; label: string; category: string; price_paise: number }[];
  show: { id: string; starts_at: string; format: string; language: string; auditorium: string };
  movie: { id: string; title: string; certificate: string; runtime_minutes: number };
  theatre: TheatreInfo; ticket_payload?: string;
}

export interface RecOption {
  seat_ids: string[]; labels: string[]; row: string; category: string; score: number; together: boolean;
  total_paise: number; reasons: string[];
}
