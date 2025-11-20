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

router = APIRouter(prefix="/projects", tags=["Project Report Avenues"])

#--------------------------------------------------------------------------------------------------
# ---------------------------- Project-Report-Avenues CRUD Operations -----------------------------
#--------------------------------------------------------------------------------------------------


#-------------------
# Report Avenues
#-------------------
@router.post("/report-avenues/", response_model=ReportAvenueOut)
def create_report_avenue(
    data: ReportAvenueCreate,
    current_user=Depends(require_role([UserRole.super_admin])),
    db: Session = Depends(get_db)
):
    # Prevent duplicates
    exists = db.query(ReportAvenue).filter(
        ReportAvenue.name.ilike(data.name),
        ReportAvenue.is_deleted == False
    ).first()

    if exists:
        raise HTTPException(400, "Report avenue already exists")

    avenue = ReportAvenue(name=data.name.strip())
    db.add(avenue)
    db.commit()
    db.refresh(avenue)
    return avenue

#------------------------------
# get all report avenues
#------------------------------
@router.get("/report-avenues/", response_model=PaginatedResponse)
def list_report_avenues(
    request: Request,
    filters: ReportAvenueFilters = Depends(),
    page: int = 1,
    page_size: int = 10,
    db: Session = Depends(get_db)
):
    query = db.query(ReportAvenue).filter(ReportAvenue.is_deleted == False)

    if filters.search:
        query = query.filter(ReportAvenue.name.ilike(f"%{filters.search}%"))

    sort_field = getattr(ReportAvenue, filters.sort_by, ReportAvenue.created_at)
    query = query.order_by(
        sort_field.asc() if filters.sort_order == "asc" else sort_field.desc()
    )

    base_url = str(request.url).split("?")[0]
    return paginate_queryset(query, page, page_size, base_url, ReportAvenueOut)


#------------------------------
# Update report avenue
#------------------------------
@router.patch("/report-avenues/{id}", response_model=ReportAvenueOut)
def update_report_avenue(
    id: uuid.UUID,
    data: ReportAvenueUpdate,
    current_user=Depends(require_role([UserRole.super_admin])),
    db: Session = Depends(get_db)
):
    avenue = db.query(ReportAvenue).filter(
        ReportAvenue.id == id,
        ReportAvenue.is_deleted == False
    ).first()

    if not avenue:
        raise HTTPException(404, "Report avenue not found")

    # Check duplicate
    if data.name:
        exists = db.query(ReportAvenue).filter(
            ReportAvenue.name.ilike(data.name),
            ReportAvenue.id != id,
            ReportAvenue.is_deleted == False
        ).first()

        if exists:
            raise HTTPException(400, "Another avenue already exists with this name")

    if data.name:
        avenue.name = data.name

    db.commit()
    db.refresh(avenue)
    return avenue


#------------------------------
# Delete report avenue
#------------------------------
@router.delete("/report-avenues/{id}", status_code=204)
def delete_report_avenue(
    id: uuid.UUID,
    current_user=Depends(require_role([UserRole.super_admin])),
    db: Session = Depends(get_db)
):
    avenue = db.query(ReportAvenue).filter(
        ReportAvenue.id == id,
        ReportAvenue.is_deleted == False
    ).first()

    if not avenue:
        raise HTTPException(404, "Report avenue not found")

    avenue.is_deleted = True
    db.commit()
    return

