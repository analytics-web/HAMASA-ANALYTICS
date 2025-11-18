# app/db/seed/category_seeder.py
from .base_seeder import BaseSeeder
from models.project import ProjectCategory


class CategorySeeder(BaseSeeder):

    CATEGORIES = [
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

    def seed(self):
        for category in self.CATEGORIES:
            self.find_or_create(ProjectCategory, category=category)
