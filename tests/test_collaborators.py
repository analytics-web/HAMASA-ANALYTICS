import uuid

def test_add_and_remove_collaborator(auth_client):

    # Create user
    user_payload = {
        "email": f"user_{uuid.uuid4().hex[:5]}@test.com",
        "first_name": "Test",
        "last_name": "User",
        "phone_number": "255700123123",
        "password": "Test1234",
        "confirm_password": "Test1234",
        "role": "org_user",
        "client_id": None
    }

    # NOTE: change endpoint for creating client users if needed
    user_res = auth_client.post("/hamasa-api/v1/client-users/", json=user_payload)
    user_id = user_res.json()["id"]

    # Create project
    project_payload = {
        "title": "Collab Test",
        "description": "desc",
        "client_id": user_res.json()["client_id"],
        "category_ids": [],
        "thematic_areas": [],
        "collaborator_ids": [],
        "media_source_ids": [],
        "report_avenue_ids": [],
        "report_time_ids": [],
        "report_consultation_ids": []
    }

    proj_res = auth_client.post("/hamasa-api/v1/projects/", json=project_payload)
    project_id = proj_res.json()["id"]

    # Add collaborator
    add_res = auth_client.post(f"/hamasa-api/v1/projects/{project_id}/collaborators/{user_id}")
    assert add_res.status_code == 200
    assert any(c["id"] == user_id for c in add_res.json()["collaborators"])

    # Remove collaborator
    remove_res = auth_client.delete(f"/hamasa-api/v1/projects/{project_id}/collaborators/{user_id}")
    assert remove_res.status_code == 200
    assert all(c["id"] != user_id for c in remove_res.json()["collaborators"])
