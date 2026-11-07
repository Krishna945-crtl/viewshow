"""Dynamic Movie Theme Engine.

Works for *any* movie, not a hard-coded list:

1. If an admin attached a custom theme -> use it (validated + clamped).
2. Otherwise score a set of visual "archetypes" (desert, ocean, cosmic, neon,
   horror, ...) against the movie's genres, mood tags and synopsis words.
3. Blend the top two archetypes, then bend the palette towards any colours the
   admin picked from the key art (`palette_hint`).
4. Nothing matched at all? Derive a harmonious palette from the title hash so
   every movie still gets its own stable look.

Last step is always `guard()` - it clamps lighting/fog/particles so seat
status colours stay readable and phones don't melt.
"""

from __future__ import annotations

import colorsys
import hashlib
import re
from typing import Any

HEX = re.compile(r"^#[0-9a-fA-F]{6}$")

PARTICLES = {"none", "dust", "sand", "embers", "bubbles", "stars", "snow", "rain", "sparks", "petals", "leaves", "mist"}
SOUNDS = {"none", "desert_wind", "deep_ocean", "space_hum", "rain", "forest", "ember_crackle", "city_night",
          "cavern", "heartbeat", "music_box", "stadium"}

# ---- archetypes ------------------------------------------------------------
# primary = dominant light colour, secondary = supporting wash, accent = highlights
ARCHETYPES: dict[str, dict[str, Any]] = {
    "desert": {
        "genres": {"adventure", "western"},
        "words": {"desert", "dune", "sand", "spice", "arrakis", "nomad", "dust", "sun", "empire", "oasis", "pharaoh", "mirage"},
        "primary": "#c8862f", "secondary": "#7a4a1e", "accent": "#f2c46b",
        "particles": "sand", "sound": "desert_wind", "fog": 0.018, "pulse": 0.15, "mood": "warm desert haze",
    },
    "ocean": {
        "genres": set(),
        "words": {"ocean", "sea", "deep", "kaiju", "monster", "titan", "underwater", "tsunami", "whale", "atlantis",
                  "submarine", "godzilla", "shark", "tide", "storm"},
        "primary": "#1e6fd9", "secondary": "#0b2a5b", "accent": "#5fd4ff",
        "particles": "bubbles", "sound": "deep_ocean", "fog": 0.03, "pulse": 0.35, "mood": "abyssal blue",
    },
    "cosmic": {
        "genres": {"science fiction", "sci-fi"},
        "words": {"space", "galaxy", "planet", "star", "alien", "orbit", "astronaut", "cosmic", "nebula", "starship",
                  "wormhole", "mars", "moon"},
        "primary": "#6c5ce7", "secondary": "#141a3d", "accent": "#a5f3fc",
        "particles": "stars", "sound": "space_hum", "fog": 0.012, "pulse": 0.25, "mood": "deep space glow",
    },
    "tech": {
        "genres": {"superhero"},
        "words": {"avengers", "hero", "multiverse", "doom", "armor", "armour", "suit", "shield", "quantum", "android",
                  "robot", "mech", "machine", "ai"},
        "primary": "#13a36b", "secondary": "#0d3b2e", "accent": "#b8c4cc",
        "particles": "sparks", "sound": "space_hum", "fog": 0.016, "pulse": 0.3, "mood": "metallic futurism",
    },
    "neon": {
        "genres": {"cyberpunk"},
        "words": {"neon", "cyber", "hacker", "city", "night", "chrome", "synth", "virtual", "glitch", "matrix", "rave"},
        "primary": "#ff2fb4", "secondary": "#2b0b52", "accent": "#00f0ff",
        "particles": "rain", "sound": "city_night", "fog": 0.022, "pulse": 0.45, "mood": "neon noir",
    },
    "horror": {
        "genres": {"horror"},
        "words": {"haunted", "ghost", "curse", "demon", "blood", "possessed", "witch", "lantern", "hollow", "evil",
                  "dark", "nightmare", "zombie"},
        "primary": "#b3122e", "secondary": "#1a0508", "accent": "#e8d9b0",
        "particles": "mist", "sound": "heartbeat", "fog": 0.034, "pulse": 0.5, "mood": "dread red",
    },
    "inferno": {
        "genres": {"war"},
        "words": {"fire", "dragon", "ash", "flame", "volcano", "battle", "war", "rage", "agni", "inferno", "burn",
                  "revenge", "blaze"},
        "primary": "#ff5a1f", "secondary": "#4a1206", "accent": "#ffc15e",
        "particles": "embers", "sound": "ember_crackle", "fog": 0.02, "pulse": 0.4, "mood": "ember glow",
    },
    "frost": {
        "genres": set(),
        "words": {"snow", "ice", "frozen", "winter", "arctic", "frost", "glacier", "cold", "blizzard", "polar"},
        "primary": "#8fd3ff", "secondary": "#1d3b56", "accent": "#ffffff",
        "particles": "snow", "sound": "desert_wind", "fog": 0.024, "pulse": 0.15, "mood": "glacial calm",
    },
    "jungle": {
        "genres": set(),
        "words": {"jungle", "forest", "tribe", "wild", "tiger", "river", "temple", "village", "safari", "rainforest",
                  "raja", "earth"},
        "primary": "#3fae4a", "secondary": "#16361b", "accent": "#e3d26f",
        "particles": "leaves", "sound": "forest", "fog": 0.022, "pulse": 0.2, "mood": "lush canopy",
    },
    "noir": {
        "genres": {"crime", "mystery", "thriller"},
        "words": {"detective", "murder", "heist", "gangster", "rain", "secret", "conspiracy", "spy", "agent", "mafia"},
        "primary": "#3aa7a3", "secondary": "#0e1f26", "accent": "#d9c08b",
        "particles": "rain", "sound": "rain", "fog": 0.026, "pulse": 0.2, "mood": "cold noir",
    },
    "romance": {
        "genres": {"romance"},
        "words": {"love", "heart", "wedding", "letters", "monsoon", "kiss", "bride", "valentine", "together"},
        "primary": "#ff6f91", "secondary": "#4b1730", "accent": "#ffd1a6",
        "particles": "petals", "sound": "rain", "fog": 0.014, "pulse": 0.2, "mood": "rose dusk",
    },
    "whimsy": {
        "genres": {"animation", "family", "kids", "comedy"},
        "words": {"magic", "toy", "pixel", "paws", "friends", "cartoon", "dream", "candy", "fun", "pet"},
        "primary": "#ffb703", "secondary": "#3a86ff", "accent": "#ff5ea8",
        "particles": "sparks", "sound": "music_box", "fog": 0.008, "pulse": 0.35, "mood": "playful pop",
    },
    "royal": {
        "genres": {"fantasy", "epic", "mythology"},
        "words": {"kingdom", "king", "queen", "throne", "sword", "legend", "myth", "god", "prince", "empire", "crown",
                  "bahu", "mahabharata", "ramayana"},
        "primary": "#8e44ad", "secondary": "#2a0f3b", "accent": "#f1c40f",
        "particles": "dust", "sound": "cavern", "fog": 0.018, "pulse": 0.25, "mood": "regal twilight",
    },
    "period": {
        "genres": {"history", "biography", "documentary", "drama"},
        "words": {"century", "freedom", "independence", "biopic", "true", "story", "colonial", "1940s", "vintage"},
        "primary": "#c49a6c", "secondary": "#3b2a1d", "accent": "#efe1c6",
        "particles": "dust", "sound": "none", "fog": 0.015, "pulse": 0.1, "mood": "sepia warmth",
    },
    "arena": {
        "genres": {"sport", "sports"},
        "words": {"cricket", "football", "match", "stadium", "team", "champion", "over", "final", "boxing", "race"},
        "primary": "#2f80ed", "secondary": "#10233f", "accent": "#f2c94c",
        "particles": "dust", "sound": "stadium", "fog": 0.01, "pulse": 0.3, "mood": "floodlight energy",
    },
}

WORD_RE = re.compile(r"[a-z0-9]+")


# ---- colour helpers ----------------------------------------------------------

def hex_to_rgb(h: str) -> tuple[float, float, float]:
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))  # type: ignore[return-value]


def rgb_to_hex(rgb) -> str:
    return "#" + "".join(f"{max(0, min(255, round(c * 255))):02x}" for c in rgb)


def mix(a: str, b: str, t: float) -> str:
    ra, rb = hex_to_rgb(a), hex_to_rgb(b)
    return rgb_to_hex(tuple(x + (y - x) * t for x, y in zip(ra, rb)))


def with_lightness(h: str, lo: float, hi: float, sat_min: float = 0.0) -> str:
    r, g, b = hex_to_rgb(h)
    hh, ll, ss = colorsys.rgb_to_hls(r, g, b)
    ll = min(hi, max(lo, ll))
    ss = max(ss, sat_min)
    return rgb_to_hex(colorsys.hls_to_rgb(hh, ll, ss))


def luminance(h: str) -> float:
    def ch(c):
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = (ch(c) for c in hex_to_rgb(h))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def from_hsl(h: float, s: float, l: float) -> str:
    return rgb_to_hex(colorsys.hls_to_rgb(h % 1.0, l, s))


# ---- scoring -----------------------------------------------------------------

def _signals(movie: dict) -> tuple[set[str], set[str], set[str]]:
    genres = {g.strip().lower() for g in movie.get("genres") or [] if g}
    tags = {t.strip().lower() for t in movie.get("mood_tags") or [] if t}
    text = " ".join(str(movie.get(k) or "") for k in ("title", "tagline", "synopsis")).lower()
    words = set(WORD_RE.findall(text))
    # tags may be multi-word ("deep sea") -> split them too
    for t in list(tags):
        words |= set(WORD_RE.findall(t))
    return genres, tags, words


def score_archetypes(movie: dict) -> list[tuple[str, float]]:
    genres, tags, words = _signals(movie)
    tag_words = set()
    for t in tags:
        tag_words |= set(WORD_RE.findall(t))
    scores = []
    for name, a in ARCHETYPES.items():
        s = 2.0 * len(genres & a["genres"])
        s += 1.5 * len(words & a["words"])
        s += 3.0 * len(tag_words & a["words"])  # tags are curated -> trust them more
        if name in tags:
            s += 6
        if s > 0:
            scores.append((name, s))
    scores.sort(key=lambda x: -x[1])
    return scores


def _title_palette(title: str) -> dict:
    digest = hashlib.sha1(title.lower().encode()).digest()
    hue = digest[0] / 255
    sat = 0.55 + digest[1] / 255 * 0.3
    return {
        "primary": from_hsl(hue, sat, 0.55),
        "secondary": from_hsl(hue + 0.04, sat * 0.8, 0.16),
        "accent": from_hsl(hue + 0.5, 0.6, 0.68),  # complementary pop
        "particles": "dust", "sound": "none", "fog": 0.015, "pulse": 0.2, "mood": "signature hue",
    }


def generate_theme(movie: dict) -> dict:
    ranked = score_archetypes(movie)
    if ranked:
        top_name, top_score = ranked[0]
        base = dict(ARCHETYPES[top_name])
        matched = [n for n, _ in ranked[:2]]
        if len(ranked) > 1 and ranked[1][1] >= top_score * 0.6:
            second = ARCHETYPES[ranked[1][0]]
            base["secondary"] = mix(base["secondary"], second["secondary"], 0.35)
            base["accent"] = mix(base["accent"], second["primary"], 0.3)
        else:
            matched = [top_name]
    else:
        base, matched = _title_palette(movie.get("title") or "untitled"), []

    hints = [c for c in (movie.get("palette_hint") or []) if isinstance(c, str) and HEX.match(c)]
    if hints:
        base["primary"] = mix(base["primary"], hints[0], 0.75)
        if len(hints) > 1:
            base["accent"] = mix(base["accent"], hints[1], 0.7)
        if len(hints) > 2:
            base["secondary"] = mix(base["secondary"], hints[2], 0.7)

    return guard(_expand(base, movie.get("title") or "Untitled", matched))


def _expand(b: dict, title: str, matched: list[str]) -> dict:
    primary, secondary, accent = b["primary"], b["secondary"], b["accent"]
    return {
        "name": f"{title} (auto)",
        "source": "auto",
        "archetypes": matched,
        "mood": b.get("mood", ""),
        "palette": {
            "primary": primary,
            "secondary": secondary,
            "accent": accent,
            "background": mix(secondary, "#000000", 0.75),
            "surface": mix(secondary, "#0b0b10", 0.55),
        },
        "lighting": {
            "ambient_color": mix(primary, "#ffffff", 0.35),
            "ambient_intensity": 0.45,
            "key_color": mix(primary, "#ffffff", 0.15),
            "key_intensity": 1.1,
            "rim_color": accent,
            "rim_intensity": 0.8,
            "wall_wash": primary,
            "floor_glow": accent,
        },
        "fog": {"color": mix(secondary, primary, 0.25), "density": b.get("fog", 0.018)},
        "screen": {"glow_color": mix(primary, "#ffffff", 0.3), "glow_intensity": 0.9,
                   "idle_gradient": [mix(secondary, "#000000", 0.3), primary, accent]},
        "particles": {"kind": b.get("particles", "dust"), "density": 0.5, "color": accent, "speed": 0.5},
        "animation": {"light_pulse": b.get("pulse", 0.2), "pulse_speed": 0.6, "transition_ms": 1800},
        "sound": {"preset": b.get("sound", "none"), "default_volume": 0.35},
        "seat_fabric": mix(secondary, primary, 0.3),
    }


DEFAULT_THEME = None  # filled lazily


def _clamp(v, lo, hi, default):
    try:
        v = float(v)
    except (TypeError, ValueError):
        return default
    return max(lo, min(hi, v))


def _color(v, default: str) -> str:
    return v if isinstance(v, str) and HEX.match(v) else default


def guard(theme: dict) -> dict:
    """Validate + clamp. Accepts partial admin input; fills gaps from defaults."""
    d = _expand(dict(_title_palette("cineverse")), theme.get("name") or "Custom", [])
    pal = {**d["palette"], **(theme.get("palette") or {})}
    pal = {k: _color(pal.get(k), d["palette"][k]) for k in d["palette"]}
    # backgrounds must stay dark so seat status colours pop
    pal["background"] = with_lightness(pal["background"], 0.02, 0.12)
    pal["surface"] = with_lightness(pal["surface"], 0.05, 0.2)
    # lights need a bit of brightness, a near-black "light" does nothing useful
    for k in ("primary", "accent"):
        pal[k] = with_lightness(pal[k], 0.35, 0.8)

    li_in = {**d["lighting"], **(theme.get("lighting") or {})}
    lighting = {
        "ambient_color": _color(li_in.get("ambient_color"), d["lighting"]["ambient_color"]),
        "ambient_intensity": _clamp(li_in.get("ambient_intensity"), 0.25, 0.9, 0.45),
        "key_color": _color(li_in.get("key_color"), d["lighting"]["key_color"]),
        "key_intensity": _clamp(li_in.get("key_intensity"), 0.4, 2.0, 1.1),
        "rim_color": _color(li_in.get("rim_color"), pal["accent"]),
        "rim_intensity": _clamp(li_in.get("rim_intensity"), 0.0, 1.6, 0.8),
        "wall_wash": _color(li_in.get("wall_wash"), pal["primary"]),
        "floor_glow": _color(li_in.get("floor_glow"), pal["accent"]),
    }
    # ambient light must not be so dim that the back rows vanish
    if luminance(lighting["ambient_color"]) < 0.08:
        lighting["ambient_color"] = with_lightness(lighting["ambient_color"], 0.45, 0.85)

    fog_in = theme.get("fog") or {}
    fog = {"color": _color(fog_in.get("color"), d["fog"]["color"]),
           "density": _clamp(fog_in.get("density"), 0.0, 0.035, 0.018)}

    sc_in = theme.get("screen") or {}
    grad = [c for c in (sc_in.get("idle_gradient") or []) if isinstance(c, str) and HEX.match(c)][:4]
    screen = {"glow_color": _color(sc_in.get("glow_color"), mix(pal["primary"], "#ffffff", 0.3)),
              "glow_intensity": _clamp(sc_in.get("glow_intensity"), 0.2, 1.5, 0.9),
              "idle_gradient": grad if len(grad) >= 2 else [pal["secondary"], pal["primary"], pal["accent"]]}

    p_in = theme.get("particles") or {}
    kind = p_in.get("kind") if p_in.get("kind") in PARTICLES else "dust"
    particles = {"kind": kind, "density": _clamp(p_in.get("density"), 0.0, 1.0, 0.5),
                 "color": _color(p_in.get("color"), pal["accent"]), "speed": _clamp(p_in.get("speed"), 0.0, 2.0, 0.5)}

    a_in = theme.get("animation") or {}
    animation = {"light_pulse": _clamp(a_in.get("light_pulse"), 0.0, 0.6, 0.2),
                 "pulse_speed": _clamp(a_in.get("pulse_speed"), 0.0, 2.0, 0.6),
                 "transition_ms": int(_clamp(a_in.get("transition_ms"), 300, 4000, 1800))}

    s_in = theme.get("sound") or {}
    sound = {"preset": s_in.get("preset") if s_in.get("preset") in SOUNDS else "none",
             "default_volume": _clamp(s_in.get("default_volume"), 0.0, 1.0, 0.35)}

    return {
        "name": str(theme.get("name") or "Custom")[:80],
        "source": theme.get("source", "custom"),
        "archetypes": list(theme.get("archetypes") or [])[:3],
        "mood": str(theme.get("mood") or "")[:80],
        "palette": pal,
        "lighting": lighting,
        "fog": fog,
        "screen": screen,
        "particles": particles,
        "animation": animation,
        "sound": sound,
        "seat_fabric": with_lightness(_color(theme.get("seat_fabric"), d["seat_fabric"]), 0.12, 0.4),
    }


def resolve_theme(movie_dict: dict, custom_config: dict | None) -> dict:
    if custom_config:
        t = guard({**custom_config, "source": "custom"})
        return t
    return generate_theme(movie_dict)
