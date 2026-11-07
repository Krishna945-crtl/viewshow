"""Demo data: fictional theatres, realistic layouts, a mix of movies, a week of shows.

    python -m app.seed            # only if the DB is empty
    python -m app.seed --reset    # wipe + reseed

Every theatre is flagged is_demo=True - nothing here pretends to be a real cinema's inventory.
"""

import asyncio
import sys
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select, text

from app.core.security import hash_password
from app.db.session import dispose_engine, sessionmaker
from app.models import Auditorium, Movie, MovieTheme, Seat, SeatCategory, Show, ShowPrice, Theatre, User
from app.services.layout import build_seats, normalise_layout
from app.services.theme_engine import guard

IST = ZoneInfo("Asia/Kolkata")

LAYOUTS = {
    "Screen 1 · Grand Arc": {
        "screen": {"width": 15, "height": 6.4, "curvature": 0.22, "distance": 7.0, "bottom": 1.5},
        "aisle_width": 1.3, "arc_focus": 24, "rise_per_row": 0.34, "flat_rows": 2,
        "rows": (
            [{"label": r, "category": "standard", "blocks": [5, 12, 5]} for r in "ABCD"]
            + [{"label": r, "category": "premium", "blocks": [6, 14, 6]} for r in "EFGHJ"]
            + [{"label": "K", "category": "vip", "blocks": [4, 10, 4], "gap_before": 0.4}]
            + [{"label": "L", "category": "recliner", "blocks": [3, 8, 3], "accessible": [1, 14]}]
        ),
    },
    "Screen 2 · Studio": {
        "screen": {"width": 11, "height": 4.6, "curvature": 0.0, "distance": 4.5, "bottom": 1.2},
        "aisle_width": 1.1, "arc_focus": 0, "rise_per_row": 0.28, "flat_rows": 1,
        "rows": (
            [{"label": r, "category": "standard", "blocks": [4, 8, 4]} for r in "ABCDE"]
            + [{"label": r, "category": "premium", "blocks": [4, 8, 4]} for r in "FG"]
            + [{"label": "H", "category": "recliner", "blocks": [2, 6, 2], "blocked": [1], "accessible": [10]}]
        ),
    },
    "Lounge · Recliners": {
        "screen": {"width": 13, "height": 5.5, "curvature": 0.12, "distance": 5.0, "bottom": 1.3},
        "aisle_width": 1.4, "arc_focus": 16, "rise_per_row": 0.42, "flat_rows": 1,
        "rows": (
            [{"label": r, "category": "vip", "blocks": [3, 6, 3]} for r in "AB"]
            + [{"label": r, "category": "recliner", "blocks": [3, 6, 3]} for r in "CDEF"]
        ),
    },
}

PRICES = {  # paise per category per layout
    "Screen 1 · Grand Arc": {"standard": 22000, "premium": 32000, "vip": 45000, "recliner": 60000},
    "Screen 2 · Studio": {"standard": 16000, "premium": 22000, "recliner": 38000},
    "Lounge · Recliners": {"vip": 55000, "recliner": 70000},
}

THEATRES = [
    ("Orbit Cinemas · Hitech City", "Hyderabad", "Plot 12, Cyber Towers Rd", ["Dolby Atmos", "Food court", "Parking"],
     ["Screen 1 · Grand Arc", "Lounge · Recliners"]),
    ("Lumen Screens · Kukatpally", "Hyderabad", "KPHB Phase 3", ["4K Laser", "Parking"],
     ["Screen 2 · Studio", "Screen 1 · Grand Arc"]),
    ("Krishna Talkies Deluxe", "Vijayawada", "MG Road, Labbipet", ["Dolby 7.1", "Wheelchair access"],
     ["Screen 2 · Studio"]),
    ("Starlight Multiplex · Indiranagar", "Bengaluru", "100 Feet Rd", ["IMAX-style screen", "Cafe"],
     ["Screen 1 · Grand Arc", "Screen 2 · Studio"]),
    ("Marina Picture Palace", "Chennai", "Beach Rd, Mylapore", ["Dolby Atmos", "Recliners"],
     ["Lounge · Recliners", "Screen 2 · Studio"]),
    ("Reel Harbour · Bandra", "Mumbai", "Linking Rd", ["4K Laser", "Bar"],
     ["Screen 1 · Grand Arc", "Lounge · Recliners"]),
]

# themes authored by an "admin" - the three reference looks from the brief
CUSTOM_THEMES = {
    "Abyssal Titan": {
        "mood": "deep ocean, electric blue",
        "palette": {"primary": "#1f7bff", "secondary": "#071a3d", "accent": "#5fe1ff",
                    "background": "#020814", "surface": "#0a1830"},
        "lighting": {"ambient_color": "#5c8fd6", "ambient_intensity": 0.42, "key_color": "#7fb6ff",
                     "key_intensity": 1.0, "rim_color": "#3fd0ff", "rim_intensity": 1.1,
                     "wall_wash": "#1f6fff", "floor_glow": "#36c8ff"},
        "fog": {"color": "#0b2f66", "density": 0.032},
        "screen": {"glow_color": "#7cc8ff", "glow_intensity": 1.0, "idle_gradient": ["#020c22", "#1352b8", "#5fe1ff"]},
        "particles": {"kind": "bubbles", "density": 0.6, "color": "#9be8ff", "speed": 0.4},
        "animation": {"light_pulse": 0.45, "pulse_speed": 0.35, "transition_ms": 2000},
        "sound": {"preset": "deep_ocean", "default_volume": 0.35},
        "seat_fabric": "#112a52",
    },
    "Emerald Doom": {
        "mood": "dark emerald, metallic futurism",
        "palette": {"primary": "#1db36b", "secondary": "#062a1c", "accent": "#c4d0d6",
                    "background": "#020a06", "surface": "#0b1f16"},
        "lighting": {"ambient_color": "#7fbf9c", "ambient_intensity": 0.4, "key_color": "#9df2c4",
                     "key_intensity": 1.15, "rim_color": "#d5e0e6", "rim_intensity": 0.9,
                     "wall_wash": "#11a35c", "floor_glow": "#47e08f"},
        "fog": {"color": "#0b3a26", "density": 0.02},
        "screen": {"glow_color": "#8ff5c0", "glow_intensity": 0.95, "idle_gradient": ["#03140c", "#0f7a47", "#c4d0d6"]},
        "particles": {"kind": "sparks", "density": 0.45, "color": "#9df2c4", "speed": 0.6},
        "animation": {"light_pulse": 0.3, "pulse_speed": 0.5, "transition_ms": 1800},
        "sound": {"preset": "space_hum", "default_volume": 0.3},
        "seat_fabric": "#1a3328",
    },
    "Spice Desert": {
        "mood": "sand, amber, bronze, desert gold",
        "palette": {"primary": "#d08a32", "secondary": "#5a3414", "accent": "#f4c76a",
                    "background": "#0d0703", "surface": "#24170c"},
        "lighting": {"ambient_color": "#d9a66b", "ambient_intensity": 0.5, "key_color": "#ffcf8a",
                     "key_intensity": 1.2, "rim_color": "#f4c76a", "rim_intensity": 0.7,
                     "wall_wash": "#c27a2c", "floor_glow": "#e8b25a"},
        "fog": {"color": "#6b4420", "density": 0.022},
        "screen": {"glow_color": "#ffd59a", "glow_intensity": 1.0, "idle_gradient": ["#2a1606", "#b3702a", "#f4c76a"]},
        "particles": {"kind": "sand", "density": 0.7, "color": "#e9c38a", "speed": 0.7},
        "animation": {"light_pulse": 0.12, "pulse_speed": 0.3, "transition_ms": 2200},
        "sound": {"preset": "desert_wind", "default_volume": 0.35},
        "seat_fabric": "#3d2814",
    },
}

MOVIES = [
    dict(title="Dune", slug="dune", theme="Spice Desert", genres=["Science Fiction", "Adventure"],
         mood_tags=["desert", "sand", "epic"], language="English", certificate="UA", runtime_minutes=155, rating=8.3,
         tagline="Reference theme: desert atmosphere",
         synopsis="An heir to a noble house is sent to govern a harsh desert world whose deep sands hide the most "
                  "valuable resource in the galaxy, and the creatures that guard it.",
         cast=["Demo cast listing"]),
    dict(title="Godzilla", slug="godzilla", theme="Abyssal Titan", genres=["Action", "Science Fiction"],
         mood_tags=["kaiju", "ocean", "storm"], language="English", certificate="UA", runtime_minutes=123, rating=7.4,
         tagline="Reference theme: deep-ocean blue",
         synopsis="A colossal creature rises from the ocean floor and coastal cities brace as scientists race to "
                  "understand whether it is a threat or a balance-keeper.", cast=["Demo cast listing"]),
    dict(title="Avengers: Doomsday", slug="avengers-doomsday", theme="Emerald Doom",
         genres=["Action", "Superhero", "Science Fiction"], mood_tags=["multiverse", "metallic", "doom"],
         language="English", certificate="UA", runtime_minutes=150, rating=None,
         tagline="Reference theme: emerald futurism",
         synopsis="Earth's heroes regroup against an armoured tyrant who threatens every reality at once.",
         cast=["Demo cast listing"]),
    # everything below has NO custom theme -> the engine works it out
    dict(title="Starfall Protocol", genres=["Science Fiction", "Thriller"], mood_tags=["space"],
         language="English", certificate="UA", runtime_minutes=132, rating=7.8,
         tagline="The last signal came from inside the station.",
         synopsis="A salvage crew boards a silent orbital station and finds the navigation AI has been rewriting "
                  "star charts for a planet that should not exist."),
    dict(title="The Hollow Lantern", genres=["Horror", "Mystery"], language="English", certificate="A",
         runtime_minutes=104, rating=7.1, tagline="Don't let the light go out.",
         synopsis="In a fog-bound hill village, a cursed lantern passes from house to house, and whoever holds it "
                  "at midnight hears the knocking."),
    dict(title="Monsoon Letters", genres=["Romance", "Drama"], language="Telugu", certificate="U",
         runtime_minutes=141, rating=8.0, tagline="Some letters take forty years to arrive.",
         synopsis="A Visakhapatnam postman finds a bundle of undelivered love letters from 1984 and sets out, "
                  "through one long monsoon, to deliver them."),
    dict(title="Neon Dharma", genres=["Cyberpunk", "Action", "Crime"], language="Hindi", certificate="A",
         runtime_minutes=128, rating=7.5, tagline="The city never logs off.",
         synopsis="A hacker-monk in a rain-soaked megacity uncovers a conspiracy hidden in the city's neon "
                  "advertising grid."),
    dict(title="Kingdom of Ash", genres=["Fantasy", "War", "Epic"], language="Telugu", certificate="UA",
         runtime_minutes=168, rating=8.4, tagline="A crown forged in fire.",
         synopsis="Two estranged princes must defend a burning kingdom from a dragon-riding warlord while a prophecy "
                  "decides which of them will sit on the throne."),
    dict(title="Frostline", genres=["Thriller", "Adventure"], mood_tags=["snow", "arctic"], language="English",
         certificate="UA", runtime_minutes=112, rating=7.2, tagline="Minus fifty. No signal. One way down.",
         synopsis="A rescue team crossing a frozen Himalayan glacier realises the stranded climbers they were sent "
                  "for do not want to be found."),
    dict(title="Pixel Paws", genres=["Animation", "Family", "Comedy"], language="English", certificate="U",
         runtime_minutes=96, rating=7.9, tagline="Eight lives left. One game to win.",
         synopsis="A clumsy street cat gets sucked into a retro video game and must team up with glitchy pixel "
                  "friends to get home before dinner."),
    dict(title="The Last Over", genres=["Sports", "Drama"], language="Tamil", certificate="U",
         runtime_minutes=138, rating=8.1, tagline="Six balls. One village.",
         synopsis="A small-town cricket team gets one shot at the state final, led by a coach who quit the game "
                  "after a single infamous over."),
    dict(title="Jungle Raja", genres=["Adventure", "Family"], mood_tags=["jungle", "forest"], language="Kannada",
         certificate="U", runtime_minutes=118, rating=7.3, tagline="The forest has a king. He is twelve.",
         synopsis="A boy raised by forest rangers protects an ancient temple and its tigers from poachers."),
    dict(title="Velvet Static", genres=[], language="English", certificate="UA", runtime_minutes=101, rating=6.9,
         tagline="(no genre data - watch the engine fall back to a title palette)",
         synopsis="An experimental film about a radio host who only broadcasts between midnight and one."),
    # real titles, NO curated theme - proof the engine handles any film from plain metadata.
    # one-line synopses are our own words; showtimes for them are simulated like everything else
    dict(title="Pushpa 2: The Rule", genres=["Action", "Crime", "Drama"], language="Telugu", certificate="UA",
         runtime_minutes=200, rating=7.6, tagline="The rule of the red forest.",
         synopsis="A red sandalwood smuggler's empire keeps growing, and so does his war with a vengeful police "
                  "officer."),
    dict(title="Kalki 2898 AD", genres=["Science Fiction", "Action", "Fantasy"], language="Telugu",
         certificate="UA", runtime_minutes=181, rating=7.4, tagline="The future has a prophecy.",
         synopsis="In the dystopian city of Kasi, a bounty hunter crosses paths with a woman who may carry the "
                  "divine avatar foretold in myth."),
    dict(title="Barbie", genres=["Comedy", "Adventure", "Fantasy"], language="English", certificate="UA",
         runtime_minutes=114, rating=7.0, tagline="A perfect world develops a glitch.",
         synopsis="Life in a colourful, perfectly pink doll world starts glitching, and one doll heads to the real "
                  "world for answers."),
    dict(title="Avatar: The Way of Water", genres=["Science Fiction", "Adventure", "Action"], language="English",
         certificate="UA", runtime_minutes=192, rating=7.6, tagline="Return to the reef.",
         synopsis="A family on a distant moon flees into the ocean reefs and learns to live with the sea clans and "
                  "their whale-like companions."),
    dict(title="Top Gun: Maverick", genres=["Action", "Drama"], language="English", certificate="UA",
         runtime_minutes=131, rating=8.2, tagline="One last mission above the clouds.",
         synopsis="A veteran naval aviator returns to train a squadron of young fighter-jet pilots for a "
                  "near-impossible mission."),
    dict(title="Oppenheimer", genres=["Drama", "History"], language="English", certificate="UA",
         runtime_minutes=180, rating=8.4, tagline="One equation. One long shadow.",
         synopsis="The physicist who led the race to build the atomic bomb during World War II, and the long shadow "
                  "it cast over his life."),
    dict(title="La La Land", genres=["Romance", "Music", "Comedy", "Drama"], language="English", certificate="U",
         runtime_minutes=128, rating=7.9, tagline="Two dreamers, one city.",
         synopsis="A jazz pianist and an aspiring actress fall in love while chasing their dreams in Los Angeles."),
    dict(title="Kantara", genres=["Action", "Drama", "Thriller"], language="Kannada", certificate="UA",
         runtime_minutes=148, rating=8.2, tagline="The forest remembers.",
         synopsis="A fiery young man in a coastal forest village is drawn into his ancestors' traditions and the "
                  "divine spirit that guards the land."),
    dict(title="Interstellar", genres=["Science Fiction", "Adventure", "Drama"], language="English",
         certificate="UA", runtime_minutes=169, rating=8.7, tagline="Beyond the wormhole.",
         synopsis="Explorers travel through a wormhole near Saturn to find a new home planet as crops fail back "
                  "home."),
]

SLOTS = [time(10, 0), time(13, 30), time(17, 0), time(20, 45)]


def slugify(t: str) -> str:
    import re
    return re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-")


async def reset(db):
    await db.execute(text(
        "TRUNCATE webhook_events, payments, booking_seats, bookings, show_prices, shows, seats, auditoriums, "
        "theatres, movies, movie_themes, refresh_tokens, users, error_logs RESTART IDENTITY CASCADE"))
    await db.commit()


async def seed(db, days: int = 6):
    db.add_all([
        User(email="admin@cineverse.dev", full_name="Cine Admin", password_hash=hash_password("Admin@123"),
             is_admin=True, city="Hyderabad"),
        User(email="demo@cineverse.dev", full_name="Demo Viewer", password_hash=hash_password("Demo@1234"),
             city="Hyderabad"),
    ])

    themes = {}
    for name, cfg in CUSTOM_THEMES.items():
        t = MovieTheme(name=name, config=guard({**cfg, "name": name}))
        db.add(t)
        themes[name] = t
    await db.flush()

    movies = []
    today = date.today()
    for i, m in enumerate(MOVIES):
        data = dict(m)
        theme = data.pop("theme", None)
        data.setdefault("slug", slugify(data["title"]))
        movie = Movie(**data, release_date=today - timedelta(days=3 * i),
                      theme_id=themes[theme].id if theme else None)
        db.add(movie)
        movies.append(movie)
    await db.flush()

    auds = []
    for name, city, addr, amen, layout_names in THEATRES:
        th = Theatre(name=name, city=city, address=addr, amenities=amen, is_demo=True)
        db.add(th)
        await db.flush()
        for ln in layout_names:
            layout = normalise_layout(LAYOUTS[ln])
            a = Auditorium(theatre_id=th.id, name=ln, layout=layout, dimensions_verified=False)
            db.add(a)
            await db.flush()
            for s in build_seats(layout):
                db.add(Seat(auditorium_id=a.id, row_label=s.row_label, number=s.number, label=s.label,
                            category=s.category, block=s.block, x=s.x, y=s.y, z=s.z, yaw=s.yaw,
                            grid_col=s.grid_col, grid_row=s.grid_row, is_blocked=s.is_blocked,
                            is_accessible=s.is_accessible))
            auds.append((a, ln))
    await db.flush()

    rot = 0
    for d in range(days):
        day = today + timedelta(days=d)
        for idx, (a, ln) in enumerate(auds):
            for slot in SLOTS:
                movie = movies[(rot + idx) % len(movies)]
                rot += 1
                starts = datetime.combine(day, slot, IST)
                fmt = "IMAX-style" if "Grand" in ln else ("4K Recliner" if "Lounge" in ln else "2D")
                show = Show(movie_id=movie.id, auditorium_id=a.id, starts_at=starts, format=fmt,
                            language=movie.language)
                show.prices = [ShowPrice(category=SeatCategory(k), price_paise=v) for k, v in PRICES[ln].items()]
                db.add(show)
    await db.commit()


async def main():
    async with sessionmaker()() as db:
        if "--reset" in sys.argv:
            await reset(db)
        elif (await db.execute(select(User.id).limit(1))).first():
            print("database already has data - use --reset to wipe it")
            return
        await seed(db)
        print("seeded: movies=%d theatres=%d" % (len(MOVIES), len(THEATRES)))
    await dispose_engine()


if __name__ == "__main__":
    asyncio.run(main())
