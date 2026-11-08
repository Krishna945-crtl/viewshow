"""Poster uploads + importing any movie from TMDB (TMDB is faked with httpx.MockTransport)."""

import httpx
import pytest

from app.main import app
from app.services.theme_engine import hls, hue_gap
from app.services.tmdb import TMDBClient, get_tmdb, to_movie_fields
from tests.test_palette import poster

PINK = poster(("#ff3fa4", 6), ("#14081a", 3), ("#7ee8fa", 1))

DETAILS = {
    "id": 4242, "title": "Glass Lagoon", "original_language": "te", "tagline": "Nothing stays buried.",
    "overview": "A diver searching a coral reef finds a sunken temple.", "runtime": 141,
    "release_date": "2026-05-01", "vote_average": 7.84, "poster_path": "/glass.png", "backdrop_path": "/bg.jpg",
    "genres": [{"id": 12, "name": "Adventure"}, {"id": 53, "name": "Thriller"}],
    "keywords": {"keywords": [{"id": 1, "name": "underwater"}, {"id": 2, "name": "shipwreck"}]},
    "credits": {"cast": [{"name": "Actor One"}, {"name": "Actor Two"}]},
    "videos": {"results": [
        {"site": "YouTube", "type": "Teaser", "key": "teaser1", "official": True},
        {"site": "YouTube", "type": "Trailer", "key": "fanmade", "official": False},
        {"site": "YouTube", "type": "Trailer", "key": "real123", "official": True},
    ]},
    "release_dates": {"results": [
        {"iso_3166_1": "US", "release_dates": [{"certification": "PG-13"}]},
        {"iso_3166_1": "IN", "release_dates": [{"certification": ""}, {"certification": "UA 13+"}]},
    ]},
}


def fake_tmdb(request: httpx.Request) -> httpx.Response:
    path = request.url.path
    if request.url.host == "image.tmdb.org":
        return httpx.Response(200, content=PINK) if path.endswith("/glass.png") else httpx.Response(404)
    assert request.url.params.get("api_key") == "test-key"
    if path == "/3/search/movie":
        return httpx.Response(200, json={"results": [
            {"id": 4242, "title": "Glass Lagoon", "release_date": "2026-05-01", "original_language": "te",
             "overview": "A diver...", "poster_path": "/glass.png", "vote_average": 7.8},
            {"id": 77, "title": "Glass Lagoon 2", "release_date": "", "original_language": "xx"},
        ]})
    if path == "/3/movie/4242":
        return httpx.Response(200, json=DETAILS)
    return httpx.Response(404, json={"status_message": "not found"})


@pytest.fixture
def tmdb():
    async def override():
        c = TMDBClient(api_key="test-key", transport=httpx.MockTransport(fake_tmdb))
        try:
            yield c
        finally:
            await c.aclose()

    app.dependency_overrides[get_tmdb] = override
    yield
    app.dependency_overrides.pop(get_tmdb, None)


async def _movie(client, headers, title="Artwork Test"):
    r = await client.post("/admin/movies", headers=headers, json={"title": title, "genres": ["Drama"]})
    assert r.status_code == 201, r.text
    return r.json()


# ---- artwork --------------------------------------------------------------------------------

async def test_upload_keeps_only_colours_by_default(client, register):
    h, _ = await register(admin=True)
    m = await _movie(client, h, "Colour Only")
    r = await client.post(f"/admin/movies/{m['id']}/artwork", headers=h,
                          files={"file": ("p.png", PINK, "image/png")})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["art_palette"][0]["hex"] == "#ff3fa4"
    assert body["poster_url"] is None  # image was not stored
    assert body["theme"]["explain"]["palette_from"] == "poster colours"
    assert hue_gap(hls(body["theme"]["palette"]["primary"])[0], hls("#ff3fa4")[0]) < 25


async def test_upload_can_keep_a_licensed_poster(client, register):
    h, _ = await register(admin=True)
    m = await _movie(client, h, "Keep Poster")
    r = await client.post(f"/admin/movies/{m['id']}/artwork", headers=h, data={"keep_image": "true"},
                          files={"file": ("p.png", PINK, "image/png")})
    url = r.json()["poster_url"]
    assert url.startswith("/media/posters/") and url.endswith(".png")
    served = await client.get(f"http://test{url}")
    assert served.status_code == 200 and served.content == PINK

    r = await client.delete(f"/admin/movies/{m['id']}/artwork", headers=h)
    assert r.json()["poster_url"] is None and r.json()["art_palette"] == []
    assert (await client.get(f"http://test{url}")).status_code == 404


async def test_upload_rejects_junk_and_non_admins(client, register):
    h, _ = await register(admin=True)
    m = await _movie(client, h, "Junk Upload")
    r = await client.post(f"/admin/movies/{m['id']}/artwork", headers=h,
                          files={"file": ("x.png", b"not really a png", "image/png")})
    assert r.status_code == 400 and r.json()["detail"]["code"] == "bad_image"

    user_h, _ = await register("viewer")
    r = await client.post(f"/admin/movies/{m['id']}/artwork", headers=user_h,
                          files={"file": ("p.png", PINK, "image/png")})
    assert r.status_code == 403


async def test_public_art_preview_stores_nothing(client):
    r = await client.post("/themes/preview-art", files={"file": ("p.png", PINK, "image/png")})
    assert r.status_code == 200
    art = r.json()["art_palette"]
    t = (await client.post("/themes/preview", json={"title": "Any Film", "art_palette": art})).json()
    assert t["explain"]["palette_from"] == "poster colours"


# ---- TMDB -----------------------------------------------------------------------------------

def test_tmdb_mapping():
    f = to_movie_fields(DETAILS, region="IN", show_posters=False)
    assert f["language"] == "Telugu"
    assert f["certificate"] == "UA 13+"
    assert f["trailer_url"] == "https://www.youtube.com/watch?v=real123"  # official trailer, not the teaser
    assert f["keywords"] == ["underwater", "shipwreck"]
    assert f["rating"] == 7.8 and f["runtime_minutes"] == 141
    assert f["poster_url"] is None and f["backdrop_url"] is None
    assert to_movie_fields(DETAILS, region="FR")["certificate"] == "UA"  # no French cert -> safe default


async def test_tmdb_disabled_without_a_key(client, register):
    h, _ = await register(admin=True)
    r = await client.get("/admin/tmdb/search", params={"q": "dune"}, headers=h)
    assert r.status_code == 503 and r.json()["detail"]["code"] == "tmdb_disabled"
    assert (await client.get("/admin/tmdb/status", headers=h)).json()["enabled"] is False


async def test_tmdb_search_and_import(client, register, tmdb):
    h, _ = await register(admin=True)
    r = await client.get("/admin/tmdb/search", params={"q": "glass"}, headers=h)
    assert r.status_code == 200, r.text
    hits = r.json()
    assert hits[0]["tmdb_id"] == 4242 and hits[0]["year"] == 2026 and hits[0]["language"] == "Telugu"
    assert hits[0]["imported_id"] is None

    r = await client.post("/admin/tmdb/import/4242", headers=h)
    assert r.status_code == 201, r.text
    m = r.json()
    assert m["tmdb_id"] == 4242 and m["slug"] == "glass-lagoon"
    assert m["keywords"] == ["underwater", "shipwreck"]
    assert m["art_palette"][0]["hex"] == "#ff3fa4"
    # keywords say ocean, the poster says pink: archetype from the story, colours from the art
    assert "ocean" in m["theme"]["archetypes"]
    assert m["theme"]["explain"]["palette_from"] == "poster colours"

    # visible in the public catalogue straight away (no shows yet, so no city filter)
    assert (await client.get(f"/movies/{m['slug']}")).status_code == 200

    again = await client.post("/admin/tmdb/import/4242", headers=h)
    assert again.status_code == 409 and again.json()["detail"]["movie_id"] == m["id"]
    hits = (await client.get("/admin/tmdb/search", params={"q": "glass"}, headers=h)).json()
    assert hits[0]["imported_id"] == m["id"]


async def test_tmdb_unknown_movie(client, register, tmdb):
    h, _ = await register(admin=True)
    r = await client.post("/admin/tmdb/import/999999", headers=h)
    assert r.status_code == 404
