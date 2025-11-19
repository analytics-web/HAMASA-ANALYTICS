from tests.factories import fake_media_category, fake_media_source

def test_create_media_source(auth_client):

    # Create category first
    cat_payload = fake_media_category()
    cat_res = auth_client.post("/hamasa-api/v1/projects/media-categories/", json=cat_payload)
    category_id = cat_res.json()["id"]

    payload = fake_media_source(category_id)
    res = auth_client.post("/hamasa-api/v1/projects/media-sources/", json=payload)
    assert res.status_code == 200
    assert res.json()["name"] == payload["name"]

def test_list_media_sources(auth_client):
    res = auth_client.get("/hamasa-api/v1/projects/media-sources/")
    assert res.status_code == 200
    assert "items" in res.json()

def test_update_media_source(auth_client):
    cat_payload = fake_media_category()
    cat_res = auth_client.post("/hamasa-api/v1/projects/media-categories/", json=cat_payload)
    category_id = cat_res.json()["id"]

    src_payload = fake_media_source(category_id)
    src_res = auth_client.post("/hamasa-api/v1/projects/media-sources/", json=src_payload)
    src_id = src_res.json()["id"]

    update = {"name": src_payload["name"] + "_updated"}
    res2 = auth_client.patch(f"/hamasa-api/v1/projects/media-sources/{src_id}", json=update)

    assert res2.status_code == 200
    assert res2.json()["name"] == update["name"]

def test_delete_media_source(auth_client):
    cat_payload = fake_media_category()
    cat_res = auth_client.post("/hamasa-api/v1/projects/media-categories/", json=cat_payload)
    category_id = cat_res.json()["id"]

    src_payload = fake_media_source(category_id)
    src_res = auth_client.post("/hamasa-api/v1/projects/media-sources/", json=src_payload)
    src_id = src_res.json()["id"]

    res2 = auth_client.delete(f"/hamasa-api/v1/projects/media-sources/{src_id}")
    assert res2.status_code == 204
