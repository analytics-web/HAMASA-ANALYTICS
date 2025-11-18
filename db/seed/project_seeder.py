# # app/db/seed/project_seeder.py
# import uuid
# from .base_seeder import BaseSeeder
# from models.project import (
#     Project,
#     ProjectCategory,
#     ProjectThematicAreas,
#     MediaSource,
#     ProjectMediaSources,
#     ReportAvenue,
#     ReportTime,
#     ReportConsultation,
# )
# from models.client import Client


# class ProjectSeeder(BaseSeeder):

#     def seed(self):
#         # Ensure a client exists
#         client = self.db.query(Client).first()
#         if not client:
#             client = Client(
#                 id=uuid.uuid4(),
#                 name="Seed Client",
#                 email="client@example.com"
#             )
#             self.db.add(client)
#             self.db.commit()

#         project = self.find_or_create(
#             Project,
#             title="Media Monitoring Project",
#             defaults={
#                 "description": "Sample seeded project.",
#                 "client_id": client.id,
#             }
#         )

#         # Attach many-to-many
#         project.categories = self.db.query(ProjectCategory).limit(3).all()
#         project.thematic_areas = self.db.query(ProjectThematicAreas).all()
#         project.report_avenues = self.db.query(ReportAvenue).all()
#         project.report_times = self.db.query(ReportTime).limit(3).all()
#         project.report_consultations = self.db.query(ReportConsultation).all()

#         # Add media sources via junction table
#         media_sources = self.db.query(MediaSource).limit(5).all()

#         for ms in media_sources:
#             exists = (
#                 self.db.query(ProjectMediaSources)
#                 .filter_by(project_id=project.id, media_source_id=ms.id)
#                 .first()
#             )
#             if not exists:
#                 self.db.add(
#                     ProjectMediaSources(
#                         project_id=project.id,
#                         media_source_id=ms.id
#                     )
#                 )

#         self.db.commit()

import uuid
import random
from dotenv import load_dotenv
from faker import Faker
import logging

from sqlalchemy.orm import Session

from core.security import hash_password
from api.client import generate_password
from models.project import (
    Project, ProjectCategory, ProjectThematicAreas, MediaSource,  MediaCategory,
    ProjectMediaSources, ReportAvenue, ReportTime, ReportConsultation
)
from models.client import Client
from models.client_user import ClientUser
from schemas.hamasa_user import UserRole
from .base_seeder import BaseSeeder

logger = logging.getLogger(__name__)
load_dotenv()
fake = Faker('en_US')

class ProjectSeeder(BaseSeeder):

    def seed(self, num_projects: int = 5):
        """Seed multiple projects with realistic random associations"""
        logger.info(f"Starting seeding {num_projects} projects...")

        # ---------------- Seed common dependents ----------------
        categories_list = ["Politics", "Sports", "Education", "Technology", "Health", "Environment"]
        thematic_areas_list = ["Policy Analysis", "Market Research", "Audience Engagement", "Content Performance"]
        media_sources_list = [("TV", "Broadcast"), ("Radio", "Broadcast"), ("Digital Media", "Online"), ("Print", "Offline")]
        report_avenues_list = ["Mobile", "Web", "Email", "Print"]
        report_times_list = ["Daily", "Weekly", "Monthly", "Quarterly", "Annually"]
        report_consultations_list = ["On-demand", "Scheduled"]

        # Create dependents
        categories = [self.find_or_create(ProjectCategory, category=c) for c in categories_list]
        thematic_areas = [self.find_or_create(ProjectThematicAreas, area=ta, title=ta) for ta in thematic_areas_list]

        media_sources = []
        # Create MediaCategory rows (in media_categories table)
        media_category_names = sorted({cat for _, cat in media_sources_list})
        media_categories = {
            cat_name: self.find_or_create(
                MediaCategory,
                # If your MediaCategory uses 'category' instead of 'name', change to: category=cat_name
                name=cat_name
            )
            for cat_name in media_category_names
        }

        # Create MediaSource rows pointing to MediaCategory
        media_sources = []
        for name, cat_name in media_sources_list:
            mcat = media_categories[cat_name]
            media_sources.append(
                self.find_or_create(
                    MediaSource,
                    name=name,
                    category_id=mcat.id  # or use category=mcat if relationship is defined
                )
            )

        report_avenues = [self.find_or_create(ReportAvenue, name=ra) for ra in report_avenues_list]
        report_times = [self.find_or_create(ReportTime, name=rt) for rt in report_times_list]
        report_consultations = [self.find_or_create(ReportConsultation, name=rc) for rc in report_consultations_list]

        self.db.commit()

        # ---------------- Seed multiple clients & projects ----------------
        for i in range(num_projects):
            nameoforg = fake.company()
            country = fake.country()
            sector = random.choice(["Technology", "Healthcare", "Finance", "Education", "Retail", "Manufacturing", "Non-Profit"])
            first_name = fake.first_name()
            last_name = fake.last_name()
            full_name = f"{first_name} {last_name}"
            phone_number = fake.phone_number()
            email = f"{first_name.lower()}.{last_name.lower()}@{fake.domain_name()}"

            plain_password = generate_password()
            hashed_password = hash_password(plain_password)

            client = self.find_or_create(
                Client,
                defaults={
                    "name_of_organisation": nameoforg,
                    "country": country,
                    "sector": sector,
                    "contact_person": full_name,
                    "phone_number": phone_number,
                    "email": email,
                },
                name_of_organisation=nameoforg
            )

            # Client User
            user = self.db.query(ClientUser).filter_by(email=email).first()
            if not user:
                user = ClientUser(
                    client_id=client.id,
                    first_name=first_name,
                    last_name=last_name,
                    phone_number=phone_number,
                    email=email,
                    hashed_password=hashed_password,
                    role=UserRole.org_admin,
                    is_active=True
                )
                self.db.add(user)
                self.db.commit()
                self.db.refresh(user)
                logger.info(f"[{i+1}] Created client user: {email}")
            else:
                logger.info(f"[{i+1}] Client user already exists: {email}")

            # Project
            project_title = f"{nameoforg} Media Monitoring Project"
            project = self.find_or_create(
                Project,
                defaults={
                    "description": f"Sample project for {nameoforg}",
                    "client_id": client.id,
                },
                title=project_title
            )

            # Randomly attach a subset of relations
            project.categories = random.sample(categories, k=random.randint(1, min(3, len(categories))))
            project.thematic_areas = random.sample(thematic_areas, k=random.randint(1, len(thematic_areas)))
            project.report_avenues = random.sample(report_avenues, k=random.randint(1, len(report_avenues)))
            project.report_times = random.sample(report_times, k=random.randint(1, len(report_times)))
            project.report_consultations = random.sample(report_consultations, k=random.randint(1, len(report_consultations)))

            # Random media sources
            selected_media_sources = random.sample(media_sources, k=random.randint(1, len(media_sources)))
            for ms in selected_media_sources:
                exists = self.db.query(ProjectMediaSources).filter_by(project_id=project.id, media_source_id=ms.id).first()
                if not exists:
                    self.db.add(ProjectMediaSources(project_id=project.id, media_source_id=ms.id))

            self.db.commit()
            logger.info(f"[{i+1}] Project seeded: {project_title}")

        logger.info(f"All {num_projects} projects seeded successfully.")
