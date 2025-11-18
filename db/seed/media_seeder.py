# app/db/seed/media_seeder.py
from .base_seeder import BaseSeeder
from models.project import MediaCategory, MediaSource


class MediaSeeder(BaseSeeder):

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

    def seed(self):
        categories = {}

        # Seed media categories
        for cat_name in self.MEDIA_CATEGORIES:
            categories[cat_name] = self.find_or_create(MediaCategory, name=cat_name)

        # Seed media sources
        for category, sources in self.MEDIA_SOURCES.items():
            for src in sources:
                self.find_or_create(
                    MediaSource, 
                    name=src,
                    category_id=categories[category].id
                )
