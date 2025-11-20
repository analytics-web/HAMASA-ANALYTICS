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

router = APIRouter(prefix="/projects", tags=["Projects"])

#--------------------------------------------------------------------------------------------------
# ---------------------------- Project CRUD Operations --------------------------------------------
#--------------------------------------------------------------------------------------------------

#---------------------
# Create a project
# ---------------------
@router.post("/", response_model=ProjectOut)
def create_project(
    project: ProjectCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_role([
        UserRole.super_admin,
        UserRole.org_admin,
    ]))
):

    new_project = Project(
        title=project.title,
        description=project.description,
        client_id=project.client_id
    )
    db.add(new_project)
    db.commit()
    db.refresh(new_project)

    # ---------------------
    # Categories
    # ---------------------
    if project.category_ids:
        new_project.categories = db.query(ProjectCategory).filter(
            ProjectCategory.id.in_(project.category_ids)
        ).all()

    # ---------------------
    # Thematic Areas (NEW)
    # User submits "new" areas, not existing ones
    # ---------------------
    created_thematic_areas = []
    for ta in project.thematic_areas:
        new_area = ProjectThematicAreas(
            area=ta.area,
            title=ta.title,
            description=ta.description,
            monitoring_objective=ta.monitoring_objectives  # ARRAY → JSONB
        )
        db.add(new_area)
        created_thematic_areas.append(new_area)

    db.commit()
    for area in created_thematic_areas:
        db.refresh(area)
    
    new_project.thematic_areas.extend(created_thematic_areas)

    # ---------------------
    # Collaborators
    # ---------------------
    if project.collaborator_ids:
        new_project.collaborators = db.query(ClientUser).filter(
            ClientUser.id.in_(project.collaborator_ids)
        ).all()

    # ---------------------
    # Media sources
    # ---------------------
    if project.media_source_ids:
        new_project.media_sources = db.query(MediaSource).filter(
            MediaSource.id.in_(project.media_source_ids)
        ).all()

    # ---------------------
    # Report Avenues
    # ---------------------
    if project.report_avenue_ids:
        new_project.report_avenues = db.query(ReportAvenue).filter(
            ReportAvenue.id.in_(project.report_avenue_ids)
        ).all()

    if project.report_time_ids:
        new_project.report_times = db.query(ReportTime).filter(
            ReportTime.id.in_(project.report_time_ids)
        ).all()

    if project.report_consultation_ids:
        new_project.report_consultations = db.query(ReportConsultation).filter(
            ReportConsultation.id.in_(project.report_consultation_ids)
        ).all()

    db.commit()
    db.refresh(new_project)

    return new_project


#------------------------
# Read all projects
#------------------------
@router.get("/", response_model=PaginatedResponse)
def get_projects(
    request: Request,
    filters: ProjectFilters = Depends(),
    page: int = 1,
    page_size: int = 10,
    db: Session = Depends(get_db),
    current_user=Depends(require_role([
        UserRole.super_admin,
        UserRole.org_admin,
        UserRole.reviewer,
        UserRole.data_clerk,
        UserRole.org_user
    ]))
):

    query = db.query(Project).filter(Project.is_deleted == False)

    if filters.title:
        query = query.filter(Project.title.ilike(f"%{filters.title}%"))

    if filters.client_id:
        query = query.filter(Project.client_id == filters.client_id)

    if filters.status:
        query = query.filter(Project.status == filters.status)

    # Sorting
    if filters.sort == "asc":
        query = query.order_by(Project.created_at.asc())
    else:
        query = query.order_by(Project.created_at.desc())

    base_url = str(request.url).split("?")[0]

    return paginate_queryset(query, page, page_size, base_url, ProjectOut)


# --------------------------
# Update project
# --------------------------
@router.put("/{uid}/", response_model=ProjectOut)
def update_project(uid: str, payload: ProjectUpdate, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == uid, Project.is_deleted == False).first()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    update_data = payload.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(project, field, value)

    db.commit()
    db.refresh(project)
    return project


# --------------------------
# Delete project
# --------------------------
@router.delete("/{uid}/", status_code=204)
def delete_project(uid: str, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == uid, Project.is_deleted == False).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    project.is_deleted = True
    db.commit()
    return







