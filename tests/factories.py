import uuid

def fake_uuid():
    return str(uuid.uuid4())

def fake_category():
    return {
        "category": "Category " + fake_uuid()[0:5]
    }

def fake_thematic_area():
    return {
        "area": "Area " + fake_uuid()[0:5],
        "title": "Title " + fake_uuid()[0:5],
        "description": "Some description",
        "monitoring_objective": ["goal 1", "goal 2"]
    }

def fake_media_category():
    return {"name": "MediaCat " + fake_uuid()[0:5]}

def fake_media_source(category_id):
    return {
        "name": "Source " + fake_uuid()[0:5],
        "category_id": str(category_id)
    }

def fake_project(client_id, category_ids, thematic_areas):
    return {
        "title": "Project " + fake_uuid()[0:5],
        "description": "Test project",
        "client_id": client_id,
        "category_ids": category_ids,
        "thematic_areas": thematic_areas,
        "collaborator_ids": [],
        "media_source_ids": [],
        "report_avenue_ids": [],
        "report_time_ids": [],
        "report_consultation_ids": []
    }
