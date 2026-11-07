async def test_register_login_me(client, register):
    headers, body = await register("asha")
    assert body["user"]["is_admin"] is False
    me = await client.get("/auth/me", headers=headers)
    assert me.status_code == 200 and me.json()["email"] == body["user"]["email"]

    r = await client.post("/auth/login", json={"email": body["user"]["email"], "password": "Passw0rd!"})
    assert r.status_code == 200
    bad = await client.post("/auth/login", json={"email": body["user"]["email"], "password": "nope12345"})
    assert bad.status_code == 401


async def test_duplicate_email_and_weak_password(client, register):
    _, body = await register("dup")
    r = await client.post("/auth/register", json={"email": body["user"]["email"], "password": "Passw0rd!",
                                                  "full_name": "x"})
    assert r.status_code == 409
    r = await client.post("/auth/register", json={"email": "weak@example.com", "password": "12345678",
                                                  "full_name": "x"})
    assert r.status_code == 422


async def test_refresh_rotation_and_reuse_detection(client, register):
    _, body = await register("rot")
    first = body["refresh_token"]
    r1 = await client.post("/auth/refresh", json={"refresh_token": first})
    assert r1.status_code == 200
    second = r1.json()["refresh_token"]
    # replaying the old token = theft signal -> whole family revoked
    assert (await client.post("/auth/refresh", json={"refresh_token": first})).status_code == 401
    assert (await client.post("/auth/refresh", json={"refresh_token": second})).status_code == 401


async def test_admin_routes_are_protected(client, register):
    headers, _ = await register("nosy")
    assert (await client.get("/admin/stats")).status_code == 401
    assert (await client.get("/admin/stats", headers=headers)).status_code == 403
    admin, _ = await register(admin=True)
    assert (await client.get("/admin/stats", headers=admin)).status_code == 200


async def test_garbage_token_rejected(client):
    r = await client.get("/auth/me", headers={"Authorization": "Bearer not.a.jwt"})
    assert r.status_code == 401
