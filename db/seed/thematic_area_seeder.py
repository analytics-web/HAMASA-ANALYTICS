# app/db/seed/thematic_area_seeder.py
from .base_seeder import BaseSeeder
from models.project import ProjectThematicAreas


class ThematicAreaSeeder(BaseSeeder):

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
            "description": "Analysis of health sector policies and issues.",
            "monitoring_objective": "Track public health discussions.",
        },
    ]

    def seed(self):
        for data in self.THEMATIC_AREAS:
            self.find_or_create(
                ProjectThematicAreas,
                area=data["area"],
                defaults=data
            )
