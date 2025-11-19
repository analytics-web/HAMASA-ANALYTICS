def test_create_report_avenue(auth_client):
    payload = {"name": "avenue1"}
    res = auth_client.post("/hamasa-api/v1/projects/report-avenues/", json=payload)
    assert res.status_code == 200
    assert res.json()["name"] == "avenue1"

def test_list_report_avenues(auth_client):
    res = auth_client.get("/hamasa-api/v1/projects/report-avenues/")
    assert res.status_code == 200
    assert "items" in res.json()

def test_update_report_avenue(auth_client):
    payload = {"name": "avenue2"}
    res = auth_client.post("/hamasa-api/v1/projects/report-avenues/", json=payload)
    avenue_id = res.json()["id"]

    update = {"name": "avenue2_updated"}
    res2 = auth_client.patch(f"/hamasa-api/v1/projects/report-avenues/{avenue_id}", json=update)

    assert res2.status_code == 200
    assert res2.json()["name"] == update["name"]

def test_delete_report_avenue(auth_client):
    payload = {"name": "avenue3"}
    res = auth_client.post("/hamasa-api/v1/projects/report-avenues/", json=payload)
    avenue_id = res.json()["id"]

    res2 = auth_client.delete(f"/hamasa-api/v1/projects/report-avenues/{avenue_id}")
    assert res2.status_code == 204
