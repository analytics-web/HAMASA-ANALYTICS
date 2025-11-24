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

router = APIRouter(prefix="/projects", tags=["Project Thematic Areas"])



#--------------------------------------------------------------------------------------------------
# ---------------------------- Project-Thematic-Areas CRUD Operations -----------------------------
#--------------------------------------------------------------------------------------------------


#----------------------------------------------
# create Thematic Areas all admins 
#----------------------------------------------
@router.post("/thematic-areas/", response_model=ProjectThematicAreaOut)
def create_thematic_area(
    area: ProjectThematicAreaCreate,
    current_user=Depends(require_role([
        UserRole.super_admin,
        UserRole.org_admin,
        UserRole.reviewer,
        UserRole.data_clerk,
        UserRole.org_user
    ])),
    db: Session = Depends(get_db)
):
    # Check duplicate
    existing = db.query(ProjectThematicAreas).filter(
        ProjectThematicAreas.area.ilike(area.area)
    ).first()

    if existing:
        raise HTTPException(400, "Thematic area already exists")

    new_area = ProjectThematicAreas(
        area=area.area.strip(),
        title=area.title.strip(),
        description=area.description,
        monitoring_objective=area.monitoring_objective  # <-- list (JSONB)
    )

    db.add(new_area)
    db.commit()
    db.refresh(new_area)

    return new_area


#------------------------------
# get all thematic areas
#------------------------------
@router.get("/thematic-areas/", response_model=PaginatedResponse)
def get_thematic_areas(
    request: Request,
    filters: ThematicAreaFilters = Depends(),
    page: int = 1,
    page_size: int = 10,
    db: Session = Depends(get_db)
):
    query = db.query(ProjectThematicAreas).filter(ProjectThematicAreas.is_deleted == False)

    # Search across area, title, description
    if filters.name:
        search = f"%{filters.name}%"
        query = query.filter(
            ProjectThematicAreas.area.ilike(search) |
            ProjectThematicAreas.title.ilike(search) |
            ProjectThematicAreas.description.ilike(search)
        )

    # Sort
    sort_field = getattr(ProjectThematicAreas, filters.sort_by, ProjectThematicAreas.created_at)
    query = query.order_by(
        sort_field.asc() if filters.sort_order.lower() == "asc" else sort_field.desc()
    )

    base_url = str(request.url).split("?")[0]

    return paginate_queryset(query, page, page_size, base_url, ProjectThematicAreaOut)


#------------------------------
# get thematic area by id
#------------------------------
@router.get("/thematic-areas/{id}", response_model=ProjectThematicAreaOut)
def get_thematic_area(
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
    item = db.query(ProjectThematicAreas).filter(
        ProjectThematicAreas.id == id,
        ProjectThematicAreas.is_deleted == False
    ).first()

    if not item:
        raise HTTPException(404, "Thematic area not found")

    return item


#------------------------------
# update thematic area
#------------------------------
@router.patch("/thematic-areas/{id}", response_model=ProjectThematicAreaOut)
def update_thematic_area(
    id: uuid.UUID,
    data: ProjectThematicAreaUpdate,
    current_user=Depends(require_role([
        UserRole.super_admin,
        UserRole.org_admin,
        UserRole.reviewer
    ])),
    db: Session = Depends(get_db)
):
    area = db.query(ProjectThematicAreas).filter(
        ProjectThematicAreas.id == id,
        ProjectThematicAreas.is_deleted == False
    ).first()

    if not area:
        raise HTTPException(404, "Thematic area not found")

    # Prevent duplicate names
    if data.area:
        exists = db.query(ProjectThematicAreas).filter(
            ProjectThematicAreas.area.ilike(data.area),
            ProjectThematicAreas.id != id
        ).first()

        if exists:
            raise HTTPException(400, "Another thematic area with that name already exists")

    # Apply updates
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(area, field, value)

    db.commit()
    db.refresh(area)

    return area

#------------------------------
# delete thematic area
#------------------------------
@router.delete("/thematic-areas/{id}", status_code=204)
def delete_thematic_area(
    id: uuid.UUID,
    current_user=Depends(require_role([UserRole.super_admin])),
    db: Session = Depends(get_db)
):
    area = db.query(ProjectThematicAreas).filter(
        ProjectThematicAreas.id == id,
        ProjectThematicAreas.is_deleted == False
    ).first()

    if not area:
        raise HTTPException(404, "Thematic area not found")

    area.is_deleted = True
    db.commit()
    return
