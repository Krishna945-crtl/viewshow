import pytest

from app.services.theme_engine import (ARCHETYPES, art_roles, generate_theme, guard, hls, hue_gap, luminance,
                                       resolve_theme, score_archetypes)


@pytest.mark.parametrize("movie,expected", [
    ({"title": "Sands of Time", "genres": ["Adventure"], "synopsis": "lost in the desert dunes"}, "desert"),
    ({"title": "Abyss", "mood_tags": ["deep sea"], "synopsis": "a monster from the ocean"}, "ocean"),
    ({"title": "Orbit", "genres": ["Science Fiction"], "synopsis": "astronaut stranded on a planet"}, "cosmic"),
    ({"title": "The Haunting", "genres": ["Horror"]}, "horror"),
    ({"title": "Love in Rain", "genres": ["Romance"]}, "romance"),
    ({"title": "Toy Box", "genres": ["Animation", "Family"]}, "whimsy"),
])
def test_detects_archetype_for_unknown_movies(movie, expected):
    assert generate_theme(movie)["archetypes"][0] == expected


# real films, described only the way a listing would (genres + one line). nothing
# here is hand-tuned per title - this is the "works for any movie" check.
REAL = [
    ("Barbie", ["Comedy", "Adventure", "Fantasy"],
     "Life in a colourful, perfectly pink doll world starts glitching.", {"pop"}),
    ("Avatar: The Way of Water", ["Science Fiction", "Adventure", "Action"],
     "A family on a distant moon flees into the ocean reefs and lives with the sea clans.", {"ocean"}),
    ("Top Gun: Maverick", ["Action", "Drama"],
     "A veteran naval aviator trains a squadron of young fighter-jet pilots.", {"sky", "kinetic"}),
    ("Pushpa 2: The Rule", ["Action", "Crime", "Drama"],
     "A red sandalwood smuggler's empire grows, and so does his war with a vengeful officer.", {"underworld"}),
    ("Kalki 2898 AD", ["Science Fiction", "Action", "Fantasy"],
     "In the dystopian city of Kasi, a woman may carry the divine avatar foretold in myth.", {"mythic", "wasteland"}),
    ("Mad Max: Fury Road", ["Action", "Adventure", "Science Fiction"],
     "In a post-apocalyptic desert wasteland, a rebel flees a warlord across the sand.", {"wasteland", "desert"}),
    ("Interstellar", ["Adventure", "Drama", "Science Fiction"],
     "Explorers travel through a wormhole near Saturn to find a new home planet.", {"cosmic"}),
    ("La La Land", ["Romance", "Music", "Comedy"],
     "A jazz pianist and an aspiring actress fall in love in Los Angeles.", {"stage", "romance"}),
    ("Frozen", ["Animation", "Family", "Fantasy"],
     "A princess sets off to find her sister, whose icy powers trapped the kingdom in eternal winter.", {"frost"}),
    ("1917", ["War", "Drama", "History"],
     "Two soldiers cross enemy territory to deliver a message that will stop an attack.", {"battlefield"}),
    ("Dangal", ["Sports", "Drama", "Biography"],
     "A former wrestler trains his daughters to become world-class wrestlers.", {"arena"}),
    ("Baahubali: The Beginning", ["Action", "Drama", "Fantasy"],
     "A young man discovers he is heir to the kingdom of Mahishmati and its throne.", {"royal"}),
    ("The Conjuring", ["Horror", "Mystery"],
     "Paranormal investigators help a family terrorised by a dark presence.", {"horror"}),
    ("Inside Out 2", ["Animation", "Family", "Comedy"],
     "A teenager's mind makes room for some brand new emotions.", {"whimsy"}),
    ("The Hangover", ["Comedy"], "Three friends wake up after a bachelor party with no memory.", {"sunny"}),
    ("John Wick: Chapter 4", ["Action", "Thriller", "Crime"], "John Wick finds a way to defeat The High Table.",
     {"kinetic"}),
]


@pytest.mark.parametrize("title,genres,synopsis,family", REAL, ids=[r[0] for r in REAL])
def test_real_movies_land_in_a_sensible_family(title, genres, synopsis, family):
    t = generate_theme({"title": title, "genres": genres, "synopsis": synopsis})
    assert t["archetypes"][0] in family, t["explain"]


def test_every_real_movie_gets_its_own_look():
    themes = [generate_theme({"title": t, "genres": g, "synopsis": s}) for t, g, s, _ in REAL]
    assert len({t["palette"]["primary"] for t in themes}) == len(themes)
    # same genres + same text, different titles -> still different (signature shift)
    a = generate_theme({"title": "Gang One", "genres": ["Crime", "Thriller"]})
    b = generate_theme({"title": "Gang Two", "genres": ["Crime", "Thriller"]})
    assert a["archetypes"] == b["archetypes"]
    assert a["palette"]["primary"] != b["palette"]["primary"]


def test_every_tmdb_genre_is_understood():
    tmdb = ["Action", "Adventure", "Animation", "Comedy", "Crime", "Documentary", "Drama", "Family", "Fantasy",
            "History", "Horror", "Music", "Mystery", "Romance", "Science Fiction", "Thriller", "War", "Western"]
    for g in tmdb:
        assert score_archetypes({"title": "x", "genres": [g]}), g


def test_compound_and_alias_genres():
    assert generate_theme({"title": "x", "genres": ["Sci-Fi"]})["archetypes"][0] == "cosmic"
    assert generate_theme({"title": "x", "genres": ["Action Thriller"]})["archetypes"][0] == "kinetic"


def test_explain_says_why():
    t = generate_theme({"title": "Deep Blue", "genres": ["Thriller"], "synopsis": "sharks circle a sinking ship"})
    e = t["explain"]
    assert e["signals"][0]["archetype"] == "ocean"
    assert any("shark" in why for why in e["signals"][0]["evidence"])
    assert 0 < e["confidence"] <= 1
    assert e["palette_from"] == "archetypes"


def test_keywords_count_more_than_plain_words():
    plain = score_archetypes({"title": "x", "synopsis": "kaiju"})
    keyed = score_archetypes({"title": "x", "keywords": ["kaiju"]})
    assert dict(keyed)["ocean"] > dict(plain)["ocean"]


def test_colour_words_nudge_the_choice():
    ev = {}
    score_archetypes({"title": "x", "synopsis": "a pink pink world"}, ev)
    assert any("colour word 'pink'" in why for why in ev.get("pop", []))


def test_poster_palette_paints_the_theme():
    pink_poster = [{"hex": "#ff3fa4", "weight": 0.55}, {"hex": "#1a0b1e", "weight": 0.3},
                   {"hex": "#7ee8fa", "weight": 0.15}]
    t = generate_theme({"title": "Mystery Film", "genres": ["Drama"], "art_palette": pink_poster})
    assert t["explain"]["palette_from"] == "poster colours"
    assert hue_gap(hls(t["palette"]["primary"])[0], hls("#ff3fa4")[0]) < 25


def test_art_roles_picks_vivid_primary_and_dark_secondary():
    roles = art_roles([{"hex": "#101010", "weight": 0.6}, {"hex": "#e8401c", "weight": 0.3},
                       {"hex": "#2bb3c0", "weight": 0.1}])
    assert roles["primary"] == "#e8401c"
    assert roles["secondary"] == "#101010"
    assert roles["accent"] == "#2bb3c0"
    assert art_roles([]) is None


def test_every_movie_gets_a_theme_even_with_no_metadata():
    a = generate_theme({"title": "Qwzx"})
    b = generate_theme({"title": "Qwzx"})
    c = generate_theme({"title": "Another"})
    assert a == b  # stable
    assert a["palette"]["primary"] != c["palette"]["primary"]
    assert a["source"] == "auto"
    assert a["explain"]["palette_from"] == "title signature"


def test_palette_hint_pulls_colours():
    base = generate_theme({"title": "X", "genres": ["Horror"]})
    hinted = generate_theme({"title": "X", "genres": ["Horror"], "palette_hint": ["#00ff00"]})
    assert hinted["palette"]["primary"] != base["palette"]["primary"]
    g = int(hinted["palette"]["primary"][3:5], 16)
    assert g > 150  # leaned hard towards green
    assert hinted["explain"]["palette_from"] == "admin colours"


def test_guard_clamps_dangerous_values():
    t = guard({
        "palette": {"background": "#ffffff", "primary": "#000000"},
        "lighting": {"ambient_intensity": 9, "ambient_color": "#000000"},
        "fog": {"density": 5},
        "particles": {"kind": "lasers", "density": 99},
        "sound": {"preset": "copyrighted_theme_song"},
    })
    assert luminance(t["palette"]["background"]) < 0.05  # stays dark so seats read
    assert t["lighting"]["ambient_intensity"] <= 0.9
    assert luminance(t["lighting"]["ambient_color"]) >= 0.08
    assert t["fog"]["density"] <= 0.035
    assert t["particles"]["kind"] == "dust" and t["particles"]["density"] <= 1
    assert t["sound"]["preset"] == "none"


def test_guard_ignores_garbage_colours_and_nan():
    t = guard({"palette": {"primary": "red; drop table"}, "fog": {"density": float("nan")}})
    assert t["palette"]["primary"].startswith("#") and len(t["palette"]["primary"]) == 7
    assert t["fog"]["density"] == 0.018


def test_custom_theme_wins_and_cannot_fake_an_explanation():
    t = resolve_theme({"title": "Dune", "genres": ["Horror"]},
                      {"palette": {"primary": "#d08a32"}, "source": "auto", "explain": {"lie": True}})
    assert t["source"] == "custom"
    assert "explain" not in t


def test_all_archetypes_produce_valid_themes():
    for name in ARCHETYPES:
        t = generate_theme({"title": name, "mood_tags": [name]})
        assert t["archetypes"][0] == name
        assert guard(t) == t  # already within limits
