import uuid
from sqlalchemy.orm import Session
from app.db.database import SessionLocal, engine, Base

from models.project import (
    Project,
    ProjectCategory,
    ProjectThematicAreas,
    MediaCategory,
    MediaSource,
    ReportAvenue,
    ReportTime,
    ReportConsultation,
)
from models.client import Client  # assuming client model exists

# -------------------------------------------
# SEED VALUES
# -------------------------------------------

PROJECT_CATEGORIES = [
    "Politics",
    "Sports",
    "Education",
    "Health",
    "Economy",
    "Technology",
    "Business",
    "Governance",
    "Environment",
]

MEDIA_CATEGORIES = [
    "Television",
    "Radio",
    "Digital Media",
    "Print Media",
    "Social Media",
]

MEDIA_SOURCES = {
    "Television": ["ITV", "Star TV", "TBC", "Azam TV"],
    "Radio": ["Clouds FM", "Radio One", "TBC FM"],
    "Digital Media": ["Mwananchi Online", "The Citizen", "IPP Media"],
    "Print Media": ["Mwananchi Newspaper", "The Guardian", "Nipashe"],
    "Social Media": ["Twitter", "Facebook", "Instagram"],
}

REPORT_AVENUES = [
    "Web",
    "Mobile",
    "Email",
    "Dashboard",
]

REPORT_TIMES = [
    "Daily",
    "Weekly",
    "Monthly",
    "Quarterly",
    "Annually",
]

REPORT_CONSULTATIONS = [
    "On-Demand",
    "Scheduled",
    "Real-Time",
]

THEMATIC_AREAS = [
    {
        "area": "Governance",
        "title": "Governance Monitoring",
        "description": "Tracks political governance issues and leaders' performance.",
        "monitoring_objective": "Monitor governance trends and sentiment.",
    },
    {
        "area": "Health",
        "title": "Health Sector Monitoring",
        "description": "Analysis of health sector programs, policies, and issues.",
        "monitoring_objective": "Track public health discussions.",
    },
]

# -------------------------------------------
# SEED FUNCTION
# -------------------------------------------


def seed_data():
    db: Session = SessionLocal()

    print("Seeding data...")

    # ------------------ Seed Categories ------------------
    category_objs = []
    for cat in PROJECT_CATEGORIES:
        obj = db.query(ProjectCategory).filter_by(category=cat).first()
        if not obj:
            obj = ProjectCategory(category=cat)
            db.add(obj)
        category_objs.append(obj)

    # ------------------ Seed Media Categories + Sources ------------------
    media_category_objs = {}

    for cat_name in MEDIA_CATEGORIES:
        cat = db.query(MediaCategory).filter_by(name=cat_name).first()
        if not cat:
            cat = MediaCategory(name=cat_name)
            db.add(cat)
        media_category_objs[cat_name] = cat

    db.commit()

    # Now seed media sources under each category
    media_source_objs = []
    for cat_name, sources in MEDIA_SOURCES.items():
        for source in sources:
            existing = (
                db.query(MediaSource)
                .filter_by(name=source, category_id=media_category_objs[cat_name].id)
                .first()
            )
            if not existing:
                existing = MediaSource(
                    name=source,
                    category_id=media_category_objs[cat_name].id
                )
                db.add(existing)
            media_source_objs.append(existing)

    # ------------------ Seed Report Avenues ------------------
    avenue_objs = []
    for name in REPORT_AVENUES:
        obj = db.query(ReportAvenue).filter_by(name=name).first()
        if not obj:
            obj = ReportAvenue(name=name)
            db.add(obj)
        avenue_objs.append(obj)

    # ------------------ Seed Report Times ------------------
    time_objs = []
    for name in REPORT_TIMES:
        obj = db.query(ReportTime).filter_by(name=name).first()
        if not obj:
            obj = ReportTime(name=name)
            db.add(obj)
        time_objs.append(obj)

    # ------------------ Seed Consultations ------------------
    consultation_objs = []
    for name in REPORT_CONSULTATIONS:
        obj = db.query(ReportConsultation).filter_by(name=name).first()
        if not obj:
            obj = ReportConsultation(name=name)
            db.add(obj)
        consultation_objs.append(obj)

    # ------------------ Seed Thematic Areas ------------------
    thematic_objs = []
    for ta in THEMATIC_AREAS:
        obj = db.query(ProjectThematicAreas).filter_by(area=ta["area"]).first()
        if not obj:
            obj = ProjectThematicAreas(**ta)
            db.add(obj)
        thematic_objs.append(obj)

    db.commit()

    print("Dependent tables seeded successfully.")

    # -------------------------------------------
    # Seed a Sample Project (Optional but useful)
    # -------------------------------------------

    client = db.query(Client).first()
    if not client:
        client = Client(id=uuid.uuid4(), name="Test Client", email="client@example.com")
        db.add(client)
        db.commit()

    project = Project(
        title="Media Monitoring Project",
        description="A test project for seeding.",
        client_id=client.id,
    )

    # Attach seeded items
    project.categories = category_objs[:3]  # first 3 categories
    project.thematic_areas = thematic_objs
    project.media_sources = []  # for junction table, we insert manually later

    # Add report options
    project.report_avenues = avenue_objs[:2]
    project.report_times = time_objs[:3]
    project.report_consultations = consultation_objs[:2]

    db.add(project)
    db.commit()

    # Attach media sources via the junction table (ProjectMediaSources)
    from models.project import ProjectMediaSources

    for ms in media_source_objs[:5]:
        db.add(
            ProjectMediaSources(
                project_id=project.id,
                media_source_id=ms.id
            )
        )

    db.commit()

    print("Project seeded successfully.")
    print("All seeding completed.")


if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    seed_data()
