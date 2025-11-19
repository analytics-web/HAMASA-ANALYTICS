def test_create_report_time(auth_client):
    payload = {"name": "daily"}
    res = auth_client.post("/hamasa-api/v1/projects/report-times/", json=payload)
    assert res.status_code == 200
    assert res.json()["name"] == "daily"

def test_list_report_times(auth_client):
    res = auth_client.get("/hamasa-api/v1/projects/report-times/")
    assert res.status_code == 200
    assert "items" in res.json()

def test_update_report_time(auth_client):
    payload = {"name": "weekly"}
    res = auth_client.post("/hamasa-api/v1/projects/report-times/", json=payload)
    rtime_id = res.json()["id"]

    update = {"name": "weekly_updated"}
    res2 = auth_client.patch(f"/hamasa-api/v1/projects/report-times/{rtime_id}", json=update)

    assert res2.status_code == 200
    assert res2.json()["name"] == update["name"]

def test_delete_report_time(auth_client):
    payload = {"name": "monthly"}
    res = auth_client.post("/hamasa-api/v1/projects/report-times/", json=payload)
    rtime_id = res.json()["id"]

    res2 = auth_client.delete(f"/hamasa-api/v1/projects/report-times/{rtime_id}")
    assert res2.status_code == 204
