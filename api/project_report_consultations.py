from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import func
from sqlalchemy.orm import Session
from api.deps import require_role
from models.enums import ProjectReportConsultations
from models.project import ReportConsultation
from schemas.client import PaginatedResponse
from schemas.hamasa_user import UserRole
from schemas.project import *
from db import get_db
from utils.pagination import paginate_queryset

router = APIRouter(prefix="/projects", tags=["Project Report Consultations"])


ENUM_TO_DB = {e: e.value for e in ProjectReportConsultations}

DB_TO_ENUM = {e.value.lower(): e for e in ProjectReportConsultations}


def normalize_consultation(name: str) -> ProjectReportConsultations:
    if not name:
        return ProjectReportConsultations.daily
    return DB_TO_ENUM.get(name.lower(), ProjectReportConsultations.daily)


#--------------------------------------------------------------------------------------------------
# ---------------------------- Project-Report-Consultations CRUD Operations -----------------------
#--------------------------------------------------------------------------------------------------


#-------------------------
# Report Consultations
#-------------------------
@router.post("/report-consultations/", response_model=ReportConsultationOut)
def create_report_consultation(
    data: ReportConsultationCreate,
    current_user=Depends(require_role([UserRole.super_admin])),
    db: Session = Depends(get_db)
):

    # Validate enum
    if data.name not in ProjectReportConsultations.__members__.values():
        raise HTTPException(400, "Invalid report consultation value")

    db_name = data.name.value

    # Prevent duplicates
    exists = db.query(ReportConsultation).filter(
        func.lower(ReportConsultation.name) == func.lower(db_name),
        ReportConsultation.is_deleted == False
    ).first()

    if exists:
        raise HTTPException(400, "Report consultation already exists")

    rc = ReportConsultation(name=db_name)
    db.add(rc)
    db.commit()
    db.refresh(rc)

    return ReportConsultationOut(
        id=rc.id,
        name=data.name
    )


#------------------------------
# get all report consultations
#------------------------------
@router.get("/report-consultations/", response_model=PaginatedResponse)
def list_report_consultations(
    request: Request,
    filters: ReportConsultationFilters = Depends(),
    page: int = 1,
    page_size: int = 10,
    db: Session = Depends(get_db)
):
    query = db.query(ReportConsultation).filter(ReportConsultation.is_deleted == False)

    if filters.name:
        query = query.filter(ReportConsultation.name.ilike(f"%{filters.name}%"))

    query = query.order_by(
        ReportConsultation.created_at.asc()
        if filters.sort_order == "asc"
        else ReportConsultation.created_at.desc()
    )

    return paginate_queryset(
        query, page, page_size,
        str(request.url).split("?")[0],
        ReportConsultationOut
    )


#------------------------------
# Get report consultation by ID
#------------------------------
@router.get("/report-consultations/{id}", response_model=ReportConsultationOut)
def get_report_consultation(
    id: uuid.UUID,
    current_user=Depends(require_role([
        UserRole.super_admin,
        UserRole.org_admin,
        UserRole.reviewer,
        UserRole.data_clerk,
        UserRole.org_user
    ])),
    db: Session = Depends(get_db)
):
    rc = db.query(ReportConsultation).filter(
        ReportConsultation.id == id,
        ReportConsultation.is_deleted == False
    ).first()

    if not rc:
        raise HTTPException(404, "Report consultation not found")

    return ReportConsultationOut(
        id=rc.id,
        name=normalize_consultation(rc.name)
    )


#------------------------------
# Update report consultation
#------------------------------
@router.patch("/report-consultations/{id}")
def update_report_consultation():
    raise HTTPException(400, "Consultation types cannot be updated (enum-managed)")

#------------------------------
# Delete report consultation
#------------------------------
@router.delete("/report-consultations/{id}", status_code=204)
def delete_report_consultation(
    id: uuid.UUID,
    current_user=Depends(require_role([UserRole.super_admin])),
    db: Session = Depends(get_db)
):
    rc = db.query(ReportConsultation).filter(
        ReportConsultation.id == id,
        ReportConsultation.is_deleted == False
    ).first()

    if not rc:
        raise HTTPException(404, "Report consultation not found")

    rc.is_deleted = True
    db.commit()
