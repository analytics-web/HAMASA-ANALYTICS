import csv
from io import StringIO
from fastapi import APIRouter, Depends, HTTPException, Request, requests, status
from sqlalchemy import func
from sqlalchemy.orm import Session
from typing import List
from api.deps import require_role
from models.enums import ProjectReportTimes
from models.project import ReportTime
from models.client_user import ClientUser
from schemas.client import PaginatedResponse
from schemas.hamasa_user import UserRole
from schemas.project import *
from db import get_db
from utils.pagination import paginate_queryset

router = APIRouter(prefix="/projects", tags=["Project Report Times"])

# Enum → DB string
ENUM_TO_DB = {e: e.value for e in ProjectReportTimes}

# DB string → Enum
DB_TO_ENUM = {e.value.lower(): e for e in ProjectReportTimes}


def normalize_report_time(db_name: str) -> ProjectReportTimes:
    if not db_name:
        return ProjectReportTimes.daily  # fallback default
    return DB_TO_ENUM.get(db_name.lower(), ProjectReportTimes.daily)





#--------------------------------------------------------------------------------------------------
# ---------------------------- Project-Report_Times CRUD Operations -------------------------------
#--------------------------------------------------------------------------------------------------

#-------------------
# Create Report Times
#-------------------
@router.post("/report-times/", response_model=ReportTimeOut)
def create_report_time(
    data: ReportTimeCreate,
    current_user=Depends(require_role([UserRole.super_admin])),
    db: Session = Depends(get_db)
):
    # Enums determine valid names
    if data.name not in ProjectReportTimes.__members__.values():
        raise HTTPException(400, "Invalid report time value")

    db_name = data.name.value

    # Prevent duplicates
    exists = db.query(ReportTime).filter(
        func.lower(ReportTime.name) == func.lower(db_name),
        ReportTime.is_deleted == False
    ).first()

    if exists:
        raise HTTPException(400, "Report time already exists")

    new_time = ReportTime(name=db_name)
    db.add(new_time)
    db.commit()
    db.refresh(new_time)

    return ReportTimeOut(
        id=new_time.id,
        name=data.name
    )
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

    query = query.order_by(
        ReportTime.created_at.asc()
        if filters.sort_order == "asc"
        else ReportTime.created_at.desc()
    )

    return paginate_queryset(query, page, page_size, str(request.url).split("?")[0], ReportTimeOut)


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
        UserRole.org_user,
    ])),
    db: Session = Depends(get_db)
):
    rtime = db.query(ReportTime).filter(
        ReportTime.id == id,
        ReportTime.is_deleted == False
    ).first()

    if not rtime:
        raise HTTPException(404, "Report time not found")

    return ReportTimeOut(
        id=rtime.id,
        name=normalize_report_time(rtime.name)
    )


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

# def update_report_time():
#     raise HTTPException(400, "Report time values cannot be updated (enum-managed)")

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
