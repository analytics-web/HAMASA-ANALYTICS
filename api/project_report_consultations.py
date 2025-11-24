import csv
from io import StringIO
from fastapi import APIRouter, Depends, HTTPException, Request, requests, status
from sqlalchemy.orm import Session
from typing import List
from api.deps import require_role
from models.ml_analysis_result import MLAnalysisResult
from models.project import MediaCategory, Project,ProjectCategory, ProjectThematicAreas, MediaSource, ReportAvenue, ReportTime, ReportConsultation
from models.client_user import ClientUser
from schemas.client import PaginatedResponse
from schemas.hamasa_user import UserRole
from schemas.project import *
from db import get_db
from utils.pagination import paginate_queryset

router = APIRouter(prefix="/projects", tags=["Project Report Consultations"])

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
    exists = db.query(ReportConsultation).filter(
        ReportConsultation.name.ilike(data.name),
        ReportConsultation.is_deleted == False
    ).first()

    if exists:
        raise HTTPException(400, "Report consultation already exists")

    rc = ReportConsultation(name=data.name.strip())
    db.add(rc)
    db.commit()
    db.refresh(rc)
    return rc

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

    if filters.search:
        query = query.filter(ReportConsultation.name.ilike(f"%{filters.search}%"))

    sort_field = getattr(ReportConsultation, filters.sort_by, ReportConsultation.created_at)

    query = query.order_by(
        sort_field.asc() if filters.sort_order == "asc" else sort_field.desc()
    )

    base_url = str(request.url).split("?")[0]
    return paginate_queryset(query, page, page_size, base_url, ReportConsultationOut)


#------------------------------
# Get report consultation by ID
#------------------------------
@router.get("/report-consultations/{id}", response_model=ReportConsultationOut)
def get_report_consultation(
    id: uuid.UUID,
    current_user=Depends(require_role([UserRole.super_admin])),
    db: Session = Depends(get_db)
):
    item = db.query(ReportConsultation).filter(
        ReportConsultation.id == id,
        ReportConsultation.is_deleted == False
    ).first()

    if not item:
        raise HTTPException(404, "Report consultation not found")

    return item


#------------------------------
# Update report consultation
#------------------------------
@router.patch("/report-consultations/{id}", response_model=ReportConsultationOut)
def update_report_consultation(
    id: uuid.UUID,
    data: ReportConsultationUpdate,
    current_user=Depends(require_role([UserRole.super_admin])),
    db: Session = Depends(get_db)
):
    rc = db.query(ReportConsultation).filter(
        ReportConsultation.id == id,
        ReportConsultation.is_deleted == False
    ).first()

    if not rc:
        raise HTTPException(404, "Report consultation not found")

    if data.name:
        exists = db.query(ReportConsultation).filter(
            ReportConsultation.name.ilike(data.name),
            ReportConsultation.id != id,
            ReportConsultation.is_deleted == False
        ).first()

        if exists:
            raise HTTPException(400, "A consultation type with that name already exists")

        rc.name = data.name

    db.commit()
    db.refresh(rc)
    return rc

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
    return
