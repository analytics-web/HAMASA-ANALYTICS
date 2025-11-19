from tests.factories import fake_category

def test_create_category(auth_client):
    payload = fake_category()

    res = auth_client.post("/hamasa-api/v1/projects/categories/", json=payload)
    assert res.status_code == 200
    assert res.json()["category"] == payload["category"]

def test_list_categories(auth_client):
    res = auth_client.get("/hamasa-api/v1/projects/categories/")
    assert res.status_code == 200
    assert "items" in res.json()
