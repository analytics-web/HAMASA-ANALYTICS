from tests.factories import fake_media_category

def test_create_media_category(auth_client):
    payload = fake_media_category()
    res = auth_client.post("/hamasa-api/v1/projects/media-categories/", json=payload)
    assert res.status_code == 200
    assert res.json()["name"] == payload["name"]

def test_list_media_categories(auth_client):
    res = auth_client.get("/hamasa-api/v1/projects/media-categories/")
    assert res.status_code == 200
    assert "items" in res.json()

def test_update_media_category(auth_client):
    payload = fake_media_category()
    res = auth_client.post("/hamasa-api/v1/projects/media-categories/", json=payload)
    cat_id = res.json()["id"]

    update = {"name": payload["name"] + "_new"}
    res2 = auth_client.patch(f"/hamasa-api/v1/projects/media-categories/{cat_id}", json=update)

    assert res2.status_code == 200
    assert res2.json()["name"] == update["name"]

def test_delete_media_category(auth_client):
    payload = fake_media_category()
    res = auth_client.post("/hamasa-api/v1/projects/media-categories/", json=payload)
    cat_id = res.json()["id"]

    res2 = auth_client.delete(f"/hamasa-api/v1/projects/media-categories/{cat_id}")
    assert res2.status_code == 204
