from tests.conftest import signup


async def test_create_random_code(client, auth):
    r = await client.post("/api/links", json={"url": "example.com/docs", "title": "Docs"}, headers=auth)
    assert r.status_code == 201
    body = r.json()
    assert len(body["code"]) == 7
    assert body["short_url"] == f"http://sn.test/{body['code']}"
    assert body["target_url"] == "https://example.com/docs"
    assert body["click_count"] == 0


async def test_custom_alias_and_conflicts(client, auth):
    ok = await client.post("/api/links", json={"url": "https://example.com", "alias": "launch"}, headers=auth)
    assert ok.status_code == 201 and ok.json()["code"] == "launch"
    taken = await client.post("/api/links", json={"url": "https://example.com", "alias": "launch"}, headers=auth)
    assert taken.status_code == 409
    reserved = await client.post("/api/links", json={"url": "https://example.com", "alias": "login"}, headers=auth)
    assert reserved.status_code == 422


async def test_rejects_unsafe_and_self_urls(client, auth):
    for url in ["javascript:alert(1)", "http://sn.test/abc"]:
        r = await client.post("/api/links", json={"url": url}, headers=auth)
        assert r.status_code == 422, url


async def test_rejects_past_or_naive_expiry(client, auth):
    for expires in ["2020-01-01T00:00:00Z", "2099-01-01T00:00:00"]:
        r = await client.post("/api/links", json={"url": "example.com", "expires_at": expires}, headers=auth)
        assert r.status_code == 422


async def test_list_search_and_paging(client, auth):
    for i in range(5):
        await client.post("/api/links", json={"url": f"https://site{i}.com", "alias": f"page-{i}"}, headers=auth)
    await client.post("/api/links", json={"url": "https://other.org", "title": "100% match_test"}, headers=auth)

    page = (await client.get("/api/links?page=1&page_size=2", headers=auth)).json()
    assert page["total"] == 6 and len(page["items"]) == 2
    assert page["items"][0]["target_url"] == "https://other.org"  # newest first

    found = (await client.get("/api/links?q=site3", headers=auth)).json()
    assert [i["code"] for i in found["items"]] == ["page-3"]
    # LIKE wildcards in the query are matched literally.
    assert (await client.get("/api/links?q=%25", headers=auth)).json()["total"] == 1


async def test_other_users_links_are_invisible(client, auth):
    link = (await client.post("/api/links", json={"url": "https://example.com"}, headers=auth)).json()
    other = await signup(client, "b@example.com")
    assert (await client.get(f"/api/links/{link['id']}", headers=other)).status_code == 404
    assert (await client.patch(f"/api/links/{link['id']}", json={"title": "x"}, headers=other)).status_code == 404
    assert (await client.delete(f"/api/links/{link['id']}", headers=other)).status_code == 404
    assert (await client.get(f"/api/links/{link['id']}/stats", headers=other)).status_code == 404
    assert (await client.get("/api/links", headers=other)).json()["total"] == 0


async def test_update_and_delete(client, auth):
    link = (await client.post("/api/links", json={"url": "https://example.com"}, headers=auth)).json()
    r = await client.patch(
        f"/api/links/{link['id']}", json={"url": "https://new.example.com", "is_active": False}, headers=auth
    )
    assert r.status_code == 200
    assert r.json()["target_url"] == "https://new.example.com" and r.json()["is_active"] is False
    assert (await client.delete(f"/api/links/{link['id']}", headers=auth)).status_code == 204
    assert (await client.get(f"/api/links/{link['id']}", headers=auth)).status_code == 404
