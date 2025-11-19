def test_create_report_consultation(auth_client):
    payload = {"name": "on-demand"}
    res = auth_client.post("/hamasa-api/v1/projects/report-consultations/", json=payload)
    assert res.status_code == 200

def test_list_report_consultations(auth_client):
    res = auth_client.get("/hamasa-api/v1/projects/report-consultations/")
    assert res.status_code == 200
    assert "items" in res.json()

def test_update_report_consultation(auth_client):
    payload = {"name": "scheduled"}
    res = auth_client.post("/hamasa-api/v1/projects/report-consultations/", json=payload)
    rc_id = res.json()["id"]

    update = {"name": "scheduled_updated"}
    res2 = auth_client.patch(f"/hamasa-api/v1/projects/report-consultations/{rc_id}", json=update)
    assert res2.status_code == 200
    assert res2.json()["name"] == update["name"]

def test_delete_report_consultation(auth_client):
    payload = {"name": "annual"}
    res = auth_client.post("/hamasa-api/v1/projects/report-consultations/", json=payload)
    rc_id = res.json()["id"]

    res2 = auth_client.delete(f"/hamasa-api/v1/projects/report-consultations/{rc_id}")
    assert res2.status_code == 204
