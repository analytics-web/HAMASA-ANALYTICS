
from sqlalchemy import func
from sqlalchemy.orm import Session

from models.enums import ProjectReportConsultations, ProjectReportTimes
from models.project import MediaCategory, ReportConsultation, ReportTime
from schemas.project import *



def get_category_by_name(db: Session, category_enum: ProjectMediaCategory):
    return db.query(MediaCategory).filter(
        MediaCategory.name.ilike(category_enum.value),
        MediaCategory.is_deleted == False
    ).first()



def seed_report_times(db: Session):
    for enum_value in ProjectReportTimes:
        exists = db.query(ReportTime).filter(
            func.lower(ReportTime.name) == func.lower(enum_value.value),
            ReportTime.is_deleted == False
        ).first()

        if not exists:
            db.add(ReportTime(name=enum_value.value))

    db.commit()



def seed_report_consultations(db: Session):
    for enum_value in ProjectReportConsultations:
        exists = db.query(ReportConsultation).filter(
            func.lower(ReportConsultation.name) == func.lower(enum_value.value),
            ReportConsultation.is_deleted == False
        ).first()

        if not exists:
            db.add(ReportConsultation(name=enum_value.value))

    db.commit()
