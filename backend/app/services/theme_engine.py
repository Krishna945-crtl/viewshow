"""Dynamic Movie Theme Engine (v2) - works for *any* movie.

How a movie gets its look:

1. Admin attached a curated theme?  -> use it (validated + clamped). Done.
2. Otherwise collect evidence from everything we know about the film:
     genres (every TMDB genre is mapped), title, tagline, synopsis, TMDB keywords,
     mood tags, colour words in the text ("red sandalwood") and the dominant
     colours of the poster / key art if one was uploaded.
3. Score ~27 visual archetypes (desert, ocean, sky, underworld, mythic ...),
   blend the top two in proportion to their scores.
4. Paint with the movie's own colours: poster palette first, admin hex picks on top.
5. Give every film a small, stable "signature" shift from its title hash so two
   crime thrillers never look identical.
6. guard() clamps everything so seat status colours stay readable and phones stay cool.

Every auto theme carries an `explain` block - which signals won and why - so an
admin can see the reasoning instead of guessing.
"""

from __future__ import annotations

import colorsys
import hashlib
import math
import re

from app.services.theme_lexicon import ARCHETYPES as _RAW, COLOUR_WORDS, GENRE_ALIASES, GENRES

HEX = re.compile(r"^#[0-9a-fA-F]{6}$")
WORD_RE = re.compile(r"[a-z0-9]+")
DECADE_RE = re.compile(r"^1[89]\d0s?$")

PARTICLES = {"none", "dust", "sand", "embers", "bubbles", "stars", "snow", "rain", "sparks", "petals", "leaves", "mist"}
SOUNDS = {"none", "desert_wind", "deep_ocean", "space_hum", "rain", "forest", "ember_crackle", "city_night",
          "cavern", "heartbeat", "music_box", "stadium", "lounge", "temple_bells"}

# how much each source counts per matched word (unique stems only)
W_TITLE, W_TEXT, W_KEYWORD, W_TAG, W_TAG_NAME = 2.5, 1.2, 2.0, 3.0, 6.0
GENRE_RANK = (1.0, 0.8, 0.65, 0.55, 0.5)  # TMDB lists the main genre first
MAX_HITS = 5


# ---- colour helpers ----------------------------------------------------------

def hex_to_rgb(h: str) -> tuple[float, float, float]:
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))  # type: ignore[return-value]


def rgb_to_hex(rgb) -> str:
    return "#" + "".join(f"{max(0, min(255, round(c * 255))):02x}" for c in rgb)


def hls(h: str) -> tuple[float, float, float]:
    return colorsys.rgb_to_hls(*hex_to_rgb(h))


def from_hsl(h: float, s: float, l: float) -> str:
    return rgb_to_hex(colorsys.hls_to_rgb(h % 1.0, l, s))


def mix(a: str, b: str, t: float) -> str:
    ra, rb = hex_to_rgb(a), hex_to_rgb(b)
    return rgb_to_hex(tuple(x + (y - x) * t for x, y in zip(ra, rb)))


def rotate(h: str, degrees: float) -> str:
    hh, ll, ss = hls(h)
    return from_hsl(hh + degrees / 360, ss, ll)


def with_lightness(h: str, lo: float, hi: float, sat_min: float = 0.0) -> str:
    hh, ll, ss = hls(h)
    eps = 0.004  # already inside the range? leave it alone so guard() stays idempotent
    if lo - eps <= ll <= hi + eps and ss >= sat_min - eps:
        return h.lower()
    return from_hsl(hh, max(ss, sat_min), min(hi, max(lo, ll)))


def luminance(h: str) -> float:
    def ch(c):
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = (ch(c) for c in hex_to_rgb(h))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def hue_gap(a: float, b: float) -> float:
    """Distance between two hues (0..1 scale) in degrees, 0..180."""
    d = abs(a - b) % 1.0
    return min(d, 1 - d) * 360


# ---- text -> stems -----------------------------------------------------------

def stem(w: str) -> str:
    # tiny plural folder - enough for "monsters", "cities", "witches". no NLP deps.
    if len(w) > 4 and w.endswith("ies"):
        return w[:-3] + "y"
    if len(w) > 4 and w.endswith("es") and (w[-3] in "sxz" or w[-4:-2] in ("ch", "sh")):
        return w[:-2]
    if len(w) > 3 and w.endswith("s") and not w.endswith(("ss", "us", "is")):
        return w[:-1]
    return w


def stems_of(text: str) -> set[str]:
    toks = [stem(t) for t in WORD_RE.findall(text.lower())]
    return set(toks) | {f"{a}_{b}" for a, b in zip(toks, toks[1:])}  # bigrams catch "deep_sea"


def _index() -> tuple[dict[str, dict], dict[str, set[str]]]:
    arche, words = {}, {}
    for name, a in _RAW.items():
        arche[name] = {k: v for k, v in a.items() if k != "words"}
        words[name] = {"_".join(stem(p) for p in w.split("_")) for w in a["words"]}
    return arche, words


ARCHETYPES, _WORDS = _index()
_HUE = {n: hls(a["primary"])[0] for n, a in ARCHETYPES.items()}


def _norm_genre(g: str) -> list[str]:
    g = g.strip().lower()
    g = GENRE_ALIASES.get(g, g)
    if g in GENRES:
        return [g]
    # "Action Thriller", "Crime & Drama" -> try the parts
    parts = [GENRE_ALIASES.get(p, p) for p in re.split(r"[\s/&,+-]+", g) if p and p != "and"]
    return [p for p in parts if p in GENRES]


# ---- evidence + scoring --------------------------------------------------------

def _colour_evidence(movie: dict, text_stems: set[str]) -> list[tuple[str, float, str]]:
    """(hex, weight, where-from) for every colour we know the film is wearing."""
    out = []
    for sw in movie.get("art_palette") or []:
        c, w = (sw.get("hex"), float(sw.get("weight") or 0)) if isinstance(sw, dict) else (None, 0)
        if isinstance(c, str) and HEX.match(c) and w > 0:
            out.append((c, min(1.0, w), "poster"))
    for word, c in COLOUR_WORDS.items():
        if word in text_stems:
            out.append((c, 0.7, f"colour word '{word}'"))
    return out


def score_archetypes(movie: dict, evidence: dict | None = None) -> list[tuple[str, float]]:
    """Rank archetypes for a movie. Pass a dict as `evidence` to collect the reasons."""
    ev = evidence if evidence is not None else {}
    score: dict[str, float] = {}

    def add(name: str, pts: float, why: str):
        if pts <= 0:
            return
        score[name] = score.get(name, 0.0) + pts
        ev.setdefault(name, []).append(why)

    # genres
    for rank, g in enumerate(movie.get("genres") or []):
        if not isinstance(g, str):
            continue
        boost = GENRE_RANK[min(rank, len(GENRE_RANK) - 1)]
        for key in _norm_genre(g):
            for name, w in GENRES[key].items():
                add(name, w * boost, f"genre {g.strip()}")

    # words. each source counts a stem once, capped so one long synopsis can't steamroll
    title = stems_of(movie.get("title") or "")
    text = stems_of(" ".join(str(movie.get(k) or "") for k in ("tagline", "synopsis")))
    keywords = stems_of(" ".join(k for k in movie.get("keywords") or [] if isinstance(k, str)))
    tags_raw = [t.strip().lower() for t in movie.get("mood_tags") or [] if isinstance(t, str) and t.strip()]
    tags = stems_of(" ".join(tags_raw))

    for name, vocab in _WORDS.items():
        for src, weight, label in ((title, W_TITLE, "title"), (text, W_TEXT, "story"),
                                   (keywords, W_KEYWORD, "keyword"), (tags, W_TAG, "mood tag")):
            hits = sorted(vocab & src)[:MAX_HITS]
            for h in hits:
                add(name, weight, f"{label} '{h.replace('_', ' ')}'")
        if name in tags_raw:
            add(name, W_TAG_NAME, f"mood tag '{name}'")

    # "set in the 1920s" -> period piece
    if any(DECADE_RE.match(t) for t in WORD_RE.findall(" ".join(
            str(movie.get(k) or "") for k in ("tagline", "synopsis")).lower())):
        add("period", W_TEXT, "story mentions a past decade")

    # colours: a pink poster leans pop/romance, a blue one ocean/cosmic
    pull: dict[str, float] = {}
    for c, w, where in _colour_evidence(movie, text | title | keywords):
        hh, ll, ss = hls(c)
        if ss < 0.3 or not 0.15 < ll < 0.9:
            continue  # greys and near-blacks say nothing about hue
        for name, ah in _HUE.items():
            close = max(0.0, 1 - hue_gap(hh, ah) / 35)
            if close:
                pull[name] = pull.get(name, 0.0) + 1.6 * w * close
                ev.setdefault(name, []).append(f"{where} {c}")
    for name, pts in pull.items():
        score[name] = score.get(name, 0.0) + min(2.5, pts)

    ranked = sorted(score.items(), key=lambda x: (-x[1], x[0]))
    return [(n, round(s, 2)) for n, s in ranked if s > 0]


# ---- palette sources -----------------------------------------------------------

def art_roles(art: list[dict]) -> dict[str, str] | None:
    """Pick primary / accent / deep colours out of an extracted poster palette."""
    cols = []
    for sw in art or []:
        c = sw.get("hex") if isinstance(sw, dict) else None
        if isinstance(c, str) and HEX.match(c):
            hh, ll, ss = hls(c)
            cols.append({"hex": c, "w": max(0.001, float(sw.get("weight") or 0)), "h": hh, "l": ll, "s": ss})
    if not cols:
        return None

    def vivid(c):  # big, saturated, mid-light colours make the best stage lights
        return (c["w"] ** 0.6) * (0.2 + c["s"]) * max(0.05, 1 - abs(c["l"] - 0.52) * 1.6)

    primary = max(cols, key=vivid)
    others = [c for c in cols if c is not primary]
    accent = max(others, key=lambda c: vivid(c) * min(1.0, 0.25 + hue_gap(c["h"], primary["h"]) / 60),
                 default=None)
    if accent is None or accent["s"] < 0.2:
        accent_hex = from_hsl(primary["h"] + 0.08, min(1, primary["s"] + 0.1), min(0.8, primary["l"] + 0.2))
    else:
        accent_hex = accent["hex"]
    deep = [c for c in cols if c["l"] < 0.35 and c["w"] > 0.05]
    deep_hex = min(deep, key=lambda c: c["l"])["hex"] if deep else from_hsl(primary["h"], primary["s"] * 0.7, 0.14)
    return {"primary": primary["hex"], "accent": accent_hex, "secondary": deep_hex}


def _signature(title: str) -> dict:
    """Stable per-title palette - also the fallback when we know nothing at all."""
    digest = hashlib.sha1(title.lower().encode()).digest()
    hue = digest[0] / 255
    sat = 0.55 + digest[1] / 255 * 0.3
    return {
        "primary": from_hsl(hue, sat, 0.55),
        "secondary": from_hsl(hue + 0.04, sat * 0.8, 0.16),
        "accent": from_hsl(hue + 0.5, 0.6, 0.68),  # complementary pop
        "particles": "dust", "sound": "none", "fog": 0.015, "pulse": 0.2, "mood": "signature hue",
        "shift": (digest[2] / 255 - 0.5) * 24,  # +-12 degrees
        "wobble": digest[3] / 255,
    }


# ---- generation ----------------------------------------------------------------

def generate_theme(movie: dict) -> dict:
    title = (movie.get("title") or "Untitled").strip() or "Untitled"
    sig = _signature(title)
    reasons: dict[str, list[str]] = {}
    ranked = score_archetypes(movie, reasons)

    matched: list[str] = []
    if ranked:
        top, s1 = ranked[0]
        base = dict(ARCHETYPES[top])
        matched = [top]
        if len(ranked) > 1 and ranked[1][1] >= 0.45 * s1:
            second, s2 = ranked[1]
            t = 0.4 * s2 / s1
            b = ARCHETYPES[second]
            base["secondary"] = mix(base["secondary"], b["secondary"], t)
            base["accent"] = mix(base["accent"], b["primary"], t * 0.9)
            base["fog"] = base["fog"] + (b["fog"] - base["fog"]) * t
            base["mood"] = f"{base['mood']} · {b['mood']}"
            matched.append(second)
        # thin evidence (one weak hint) -> lean on the title signature instead
        if s1 < 1.5:
            for k in ("primary", "secondary", "accent"):
                base[k] = mix(base[k], sig[k], 0.45)
    else:
        base = dict(sig)

    palette_from = "archetypes" if ranked else "title signature"

    # the film's own colours beat any archetype guess
    roles = art_roles(movie.get("art_palette") or [])
    if roles:
        base["primary"] = mix(base["primary"], roles["primary"], 0.7)
        base["accent"] = mix(base["accent"], roles["accent"], 0.6)
        base["secondary"] = mix(base["secondary"], roles["secondary"], 0.6)
        palette_from = "poster colours"

    hints = [c for c in (movie.get("palette_hint") or []) if isinstance(c, str) and HEX.match(c)]
    if hints:
        base["primary"] = mix(base["primary"], hints[0], 0.75)
        if len(hints) > 1:
            base["accent"] = mix(base["accent"], hints[1], 0.7)
        if len(hints) > 2:
            base["secondary"] = mix(base["secondary"], hints[2], 0.7)
        palette_from = "admin colours"

    # per-film signature: small hue drift + atmosphere wobble. smaller when the
    # colours came from real artwork, we don't want to drift away from the poster
    shift = sig["shift"] * (0.3 if (roles or hints) else 1.0) if ranked else 0.0
    if shift:
        for k in ("primary", "secondary", "accent"):
            base[k] = rotate(base[k], shift)
    base["fog"] = base.get("fog", 0.018) * (0.88 + 0.24 * sig["wobble"])
    base["pulse"] = base.get("pulse", 0.2) * (0.9 + 0.2 * sig["wobble"])

    top_score = ranked[0][1] if ranked else 0.0
    explain = {
        "confidence": round(1 - math.exp(-top_score / 5), 2),
        "palette_from": palette_from,
        "signature_shift_deg": round(shift, 1),
        "signals": [
            {"archetype": n, "label": ARCHETYPES[n]["label"], "score": s, "evidence": reasons.get(n, [])[:6]}
            for n, s in ranked[:3]
        ],
    }
    theme = _expand(base, title, matched)
    theme["explain"] = explain
    return guard(theme)


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


# ---- safety net ----------------------------------------------------------------

def _clamp(v, lo, hi, default):
    try:
        v = float(v)
    except (TypeError, ValueError):
        return default
    if math.isnan(v):
        return default
    return max(lo, min(hi, v))


def _color(v, default: str) -> str:
    return v.lower() if isinstance(v, str) and HEX.match(v) else default


_DEFAULTS = _expand(_signature("cineverse"), "Custom", [])


def guard(theme: dict) -> dict:
    """Validate + clamp. Accepts partial admin input; fills gaps from defaults."""
    d = _DEFAULTS
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
           "density": round(_clamp(fog_in.get("density"), 0.0, 0.035, 0.018), 4)}

    sc_in = theme.get("screen") or {}
    grad = [c.lower() for c in (sc_in.get("idle_gradient") or []) if isinstance(c, str) and HEX.match(c)][:4]
    screen = {"glow_color": _color(sc_in.get("glow_color"), mix(pal["primary"], "#ffffff", 0.3)),
              "glow_intensity": _clamp(sc_in.get("glow_intensity"), 0.2, 1.5, 0.9),
              "idle_gradient": grad if len(grad) >= 2 else [pal["secondary"], pal["primary"], pal["accent"]]}

    p_in = theme.get("particles") or {}
    kind = p_in.get("kind") if p_in.get("kind") in PARTICLES else "dust"
    particles = {"kind": kind, "density": _clamp(p_in.get("density"), 0.0, 1.0, 0.5),
                 "color": _color(p_in.get("color"), pal["accent"]), "speed": _clamp(p_in.get("speed"), 0.0, 2.0, 0.5)}

    a_in = theme.get("animation") or {}
    animation = {"light_pulse": round(_clamp(a_in.get("light_pulse"), 0.0, 0.6, 0.2), 3),
                 "pulse_speed": _clamp(a_in.get("pulse_speed"), 0.0, 2.0, 0.6),
                 "transition_ms": int(_clamp(a_in.get("transition_ms"), 300, 4000, 1800))}

    s_in = theme.get("sound") or {}
    sound = {"preset": s_in.get("preset") if s_in.get("preset") in SOUNDS else "none",
             "default_volume": _clamp(s_in.get("default_volume"), 0.0, 1.0, 0.35)}

    source = "auto" if theme.get("source") == "auto" else "custom"
    out = {
        "name": str(theme.get("name") or "Custom")[:80],
        "source": source,
        "archetypes": [a for a in (theme.get("archetypes") or []) if a in ARCHETYPES][:3],
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
    # the reasoning block is ours, never trust one that arrived from a request body
    if source == "auto" and isinstance(theme.get("explain"), dict):
        out["explain"] = theme["explain"]
    return out


def resolve_theme(movie_dict: dict, custom_config: dict | None) -> dict:
    if custom_config:
        return guard({**custom_config, "source": "custom"})
    return generate_theme(movie_dict)
