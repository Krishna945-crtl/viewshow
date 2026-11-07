from datetime import datetime, timedelta, timezone


async def test_movies_all_have_themes(client):
    movies = (await client.get("/movies")).json()
    assert len(movies) >= 10
    for m in movies:
        t = m["theme"]
        assert t["palette"]["primary"].startswith("#") and t["lighting"] and t["particles"]
    by_slug = {m["slug"]: m for m in movies}
    assert by_slug["dune"]["theme"]["source"] == "custom"
    assert by_slug["starfall-protocol"]["theme"]["source"] == "auto"


async def test_filters_and_showtimes(client):
    assert all("Horror" in m["genres"] for m in (await client.get("/movies", params={"genre": "horror"})).json())
    cities = [c["city"] for c in (await client.get("/cities")).json()]
    assert "Hyderabad" in cities
    st = (await client.get("/movies/dune/showtimes", params={"city": "Hyderabad"})).json()
    assert st["movie"]["slug"] == "dune"
    for t in st["theatres"]:
        assert t["theatre"]["city"] == "Hyderabad" and t["theatre"]["is_demo"] is True


async def test_recommendations_endpoint(client, show_id):
    r = await client.post(f"/shows/{show_id}/recommendations", json={"group_size": 3})
    opts = r.json()["options"]
    assert opts and len(opts[0]["seat_ids"]) == 3 and opts[0]["together"]


async def test_admin_new_movie_gets_auto_theme_then_custom(client, register):
    admin, _ = await register(admin=True)
    r = await client.post("/admin/movies", headers=admin, json={
        "title": "Tidal Wraith", "genres": ["Horror"], "mood_tags": ["ocean"],
        "synopsis": "Something in the deep sea calls the fishermen home.", "runtime_minutes": 100})
    assert r.status_code == 201, r.text
    m = r.json()
    assert m["theme"]["source"] == "auto" and set(m["theme"]["archetypes"]) & {"ocean", "horror"}

    t = await client.post("/admin/themes", headers=admin, json={"name": "Wraith Teal", "config": {
        "palette": {"primary": "#00c2a8"}, "fog": {"density": 1}}})
    assert t.status_code == 201
    assert t.json()["config"]["fog"]["density"] <= 0.035  # clamped
    upd = await client.put(f"/admin/movies/{m['id']}", headers=admin, json={
        "title": "Tidal Wraith", "genres": ["Horror"], "runtime_minutes": 100, "theme_id": t.json()["id"]})
    assert upd.json()["theme"]["source"] == "custom"
    assert upd.json()["theme"]["name"] == "Wraith Teal"


async def test_admin_theme_preview(client, register):
    admin, _ = await register(admin=True)
    r = await client.post("/admin/themes/preview", headers=admin, json={"title": "Snowbound", "genres": ["Thriller"],
                                                                        "mood_tags": ["snow"]})
    assert r.json()["particles"]["kind"] == "snow"


async def test_admin_auditorium_and_show_overlap(client, register):
    admin, _ = await register(admin=True)
    th = (await client.post("/admin/theatres", headers=admin, json={"name": "Test Hall", "city": "Pune"})).json()
    bad = await client.post(f"/admin/theatres/{th['id']}/auditoriums", headers=admin,
                            json={"name": "X", "layout": {"rows": []}})
    assert bad.status_code == 400
    aud = (await client.post(f"/admin/theatres/{th['id']}/auditoriums", headers=admin, json={
        "name": "Screen 9", "layout": {"rows": [{"label": "A", "blocks": [4, 4]}, {"label": "B", "blocks": [4, 4]}]}}
    )).json()
    assert aud["summary"]["seat_count"] == 16

    movie = (await client.get("/movies")).json()[0]
    start = (datetime.now(timezone.utc) + timedelta(days=3)).replace(microsecond=0)
    body = {"movie_id": movie["id"], "auditorium_id": aud["id"], "starts_at": start.isoformat(),
            "prices": {"standard": 15000}}
    assert (await client.post("/admin/shows", headers=admin, json=body)).status_code == 201
    body["starts_at"] = (start + timedelta(minutes=30)).isoformat()
    assert (await client.post("/admin/shows", headers=admin, json=body)).status_code == 409


async def test_admin_stats_and_errors(client, register):
    admin, _ = await register(admin=True)
    s = (await client.get("/admin/stats", headers=admin)).json()
    assert {"revenue_paise", "occupancy", "bookings_by_status", "errors_24h"} <= s.keys()
    assert (await client.get("/admin/errors", headers=admin)).status_code == 200


async def test_validation_errors_are_friendly(client, register):
    admin, _ = await register(admin=True)
    r = await client.post("/admin/movies", headers=admin, json={"title": "", "palette_hint": ["red"]})
    assert r.status_code == 422 and r.json()["detail"]["code"] == "invalid"


async def test_public_theme_playground(client):
    r = await client.post("/themes/preview", json={"title": "Glacier Run", "mood_tags": ["ice", "snow"]})
    assert r.status_code == 200 and r.json()["archetypes"][0] == "frost"
