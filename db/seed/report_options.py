# app/db/seed/report_options_seeder.py
from .base_seeder import BaseSeeder
from models.project import ReportAvenue, ReportTime, ReportConsultation


class ReportOptionsSeeder(BaseSeeder):

    AVENUES = ["Web", "Mobile", "Email", "Dashboard"]
    TIMES = ["Daily", "Weekly", "Monthly", "Quarterly", "Annually"]
    CONSULTATIONS = ["On-Demand", "Scheduled", "Real-Time"]

    def seed(self):
        for a in self.AVENUES:
            self.find_or_create(ReportAvenue, name=a)

        for t in self.TIMES:
            self.find_or_create(ReportTime, name=t)

        for c in self.CONSULTATIONS:
            self.find_or_create(ReportConsultation, name=c)
