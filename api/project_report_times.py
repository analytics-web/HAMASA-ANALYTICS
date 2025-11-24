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

router = APIRouter(prefix="/projects", tags=["Projects Report Times"])

#--------------------------------------------------------------------------------------------------
# ---------------------------- Project-Report_Times CRUD Operations -------------------------------
#--------------------------------------------------------------------------------------------------

#-------------------
# Report Times
#-------------------
@router.post("/report-times/", response_model=ReportTimeOut)
def create_report_time(
    data: ReportTimeCreate,
    current_user=Depends(require_role([UserRole.super_admin])),
    db: Session = Depends(get_db)
):
    exists = db.query(ReportTime).filter(
        ReportTime.name.ilike(data.name),
        ReportTime.is_deleted == False
    ).first()

    if exists:
        raise HTTPException(400, "Report time already exists")

    new_time = ReportTime(name=data.name.strip())
    db.add(new_time)
    db.commit()
    db.refresh(new_time)
    return new_time


#------------------------------
# get all report times
#------------------------------
@router.get("/report-times/", response_model=PaginatedResponse)
def list_report_times(
    request: Request,
    filters: ReportTimeFilters = Depends(),
    page: int = 1,
    page_size: int = 10,
    db: Session = Depends(get_db)
):
    query = db.query(ReportTime).filter(ReportTime.is_deleted == False)

    if filters.name:
        query = query.filter(ReportTime.name.ilike(f"%{filters.name}%"))

    sort_field = getattr(ReportTime, filters.sort_by, ReportTime.created_at)
    query = query.order_by(
        sort_field.asc() if filters.sort_order == "asc" else sort_field.desc()
    )

    base_url = str(request.url).split("?")[0]
    return paginate_queryset(query, page, page_size, base_url, ReportTimeOut)


#------------------------------
# Get one report time
#------------------------------
@router.get("/report-times/{id}", response_model=ReportTimeOut)
def get_report_time(
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
    item = db.query(ReportTime).filter(
        ReportTime.id == id,
        ReportTime.is_deleted == False
    ).first()

    if not item:
        raise HTTPException(404, "Report time not found")

    return item


#------------------------------
# Update report time
#------------------------------
@router.patch("/report-times/{id}", response_model=ReportTimeOut)
def update_report_time(
    id: uuid.UUID,
    data: ReportTimeUpdate,
    current_user=Depends(require_role([UserRole.super_admin])),
    db: Session = Depends(get_db)
):
    rtime = db.query(ReportTime).filter(
        ReportTime.id == id,
        ReportTime.is_deleted == False
    ).first()

    if not rtime:
        raise HTTPException(404, "Report time not found")

    if data.name:
        exists = db.query(ReportTime).filter(
            ReportTime.name.ilike(data.name),
            ReportTime.id != id,
            ReportTime.is_deleted == False
        ).first()

        if exists:
            raise HTTPException(400, "Another report time already exists with this name")

        rtime.name = data.name

    db.commit()
    db.refresh(rtime)
    return rtime


#------------------------------
# Delete report time
#------------------------------
@router.delete("/report-times/{id}", status_code=204)
def delete_report_time(
    id: uuid.UUID,
    current_user=Depends(require_role([UserRole.super_admin])),
    db: Session = Depends(get_db)
):
    rtime = db.query(ReportTime).filter(
        ReportTime.id == id,
        ReportTime.is_deleted == False
    ).first()

    if not rtime:
        raise HTTPException(404, "Report time not found")

    rtime.is_deleted = True
    db.commit()
    return
