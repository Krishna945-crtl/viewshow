import pytest

from app.services.theme_engine import ARCHETYPES, generate_theme, guard, luminance, resolve_theme


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


def test_every_movie_gets_a_theme_even_with_no_metadata():
    a = generate_theme({"title": "Qwzx"})
    b = generate_theme({"title": "Qwzx"})
    c = generate_theme({"title": "Another"})
    assert a == b  # stable
    assert a["palette"]["primary"] != c["palette"]["primary"]
    assert a["source"] == "auto"


def test_palette_hint_pulls_colours():
    base = generate_theme({"title": "X", "genres": ["Horror"]})
    hinted = generate_theme({"title": "X", "genres": ["Horror"], "palette_hint": ["#00ff00"]})
    assert hinted["palette"]["primary"] != base["palette"]["primary"]
    g = int(hinted["palette"]["primary"][3:5], 16)
    assert g > 150  # leaned hard towards green


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


def test_guard_ignores_garbage_colours():
    t = guard({"palette": {"primary": "red; drop table"}})
    assert t["palette"]["primary"].startswith("#") and len(t["palette"]["primary"]) == 7


def test_custom_theme_wins():
    t = resolve_theme({"title": "Dune", "genres": ["Horror"]}, {"palette": {"primary": "#d08a32"}})
    assert t["source"] == "custom"


def test_all_archetypes_produce_valid_themes():
    for name in ARCHETYPES:
        t = generate_theme({"title": name, "mood_tags": [name]})
        assert t["archetypes"][0] == name
        assert guard(t) == t  # already within limits
