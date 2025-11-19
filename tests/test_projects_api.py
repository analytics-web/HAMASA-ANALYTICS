from tests.factories import fake_category, fake_thematic_area, fake_project

def test_create_project(auth_client):

    # Create a category
    cat_res = auth_client.post("/hamasa-api/v1/projects/categories/", json=fake_category())
    category_id = cat_res.json()["id"]

    # Create Thematic Area
    ta_payload = fake_thematic_area()
    ta_res = auth_client.post("/hamasa-api/v1/projects/thematic-areas/", json=ta_payload)
    thematic_area = ta_res.json()

    # Create project
    project_payload = {
        "title": "Test Project",
        "description": "Test Description",
        "client_id": thematic_area["id"],   # temporary fake
        "category_ids": [category_id],
        "thematic_areas": [ta_payload],
        "collaborator_ids": [],
        "media_source_ids": [],
        "report_avenue_ids": [],
        "report_time_ids": [],
        "report_consultation_ids": []
    }

    res = auth_client.post("/hamasa-api/v1/projects/", json=project_payload)
    assert res.status_code == 200
    assert res.json()["title"] == "Test Project"
