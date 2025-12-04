# ------------------------------------------------------------
# PROJECT CREATE / UPDATE (SAFE, FIXED, VALIDATION-PROOF)
# ------------------------------------------------------------

import json
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import func

from api.deps import require_role
from db import get_db
from models.client_user import ClientUser
from models.enums import ProjectStatus
from models.project_progress import ProjectProgress
from schemas.client import PaginatedResponse
from schemas.hamasa_user import UserRole
from schemas.project import (
    ALLOWED_STATUS_TRANSITIONS,
    ProjectCreate,
    ProjectFilters,
    ProjectOutSafe,
    ProjectProgressOut,
    ProjectStatusUpdate,
    ProjectUpdate,
)
from models.project import (
    Project,
    ProjectCategory,
    ProjectThematicAreas,
    ProjectMediaSources,
    MediaSource,
    ReportAvenue,
    ReportTime,
    ReportConsultation
)



router = APIRouter(prefix="/projects", tags=["Projects"])


# -------------------------------------------------------
# CREATE PROJECT
# -------------------------------------------------------
@router.post("/", response_model=ProjectOutSafe)
def create_project(
    payload: ProjectCreate,
    db: Session = Depends(get_db),
    current_user=Depends(
        require_role([
            UserRole.super_admin,
            UserRole.org_admin,
        ])
    ),
):
    try:
        # -------------------------------------------------------------
        # STEP 0 — Determine client_id based on user role
        # -------------------------------------------------------------
        if current_user["role"] == UserRole.super_admin:
            # super admin may specify any client_id (payload already has it)
            client_id = payload.client_id

        elif current_user["role"] == UserRole.org_admin:
            # org admin MUST use their own assigned client_id
            client_id = current_user["client_id"]

        else:
            raise HTTPException(403, "You are not allowed to create projects")

        # -------------------------------------------------------------
        # STEP 1 — Create base project
        # -------------------------------------------------------------
        project = Project(
            title=payload.title,
            description=payload.description,
            client_id=client_id,
            status=ProjectStatus.draft
        )

        db.add(project)
        db.flush()  # ensures project.id is generated

        # -------------------------------------------------------------
        # STEP 2 — Categories
        # -------------------------------------------------------------
        if payload.category_ids:
            project.categories = db.query(ProjectCategory).filter(
                ProjectCategory.id.in_(payload.category_ids)
            ).all()

        # -------------------------------------------------------------
        # STEP 3 — Thematic Areas
        # -------------------------------------------------------------
        created_ta = []
        for ta in payload.thematic_areas:
            new_ta = ProjectThematicAreas(
                area=ta.area,
                title=ta.title,
                description=ta.description,
                monitoring_objective=(
                    json.dumps(ta.monitoring_objectives)
                    if isinstance(ta.monitoring_objectives, list)
                    else ta.monitoring_objectives
                )
            )
            db.add(new_ta)
            created_ta.append(new_ta)

        db.flush()
        project.thematic_areas.extend(created_ta)

        # -------------------------------------------------------------
        # STEP 4 — Collaborators
        # -------------------------------------------------------------
        if payload.collaborator_ids:
            project.collaborators = db.query(ClientUser).filter(
                ClientUser.id.in_(payload.collaborator_ids)
            ).all()

        # -------------------------------------------------------------
        # STEP 5 — Media Sources (junction)
        # -------------------------------------------------------------
        if payload.media_source_ids:
            db.add_all([
                ProjectMediaSources(
                    project_id=project.id,
                    media_source_id=ms_id
                )
                for ms_id in payload.media_source_ids
            ])

        # -------------------------------------------------------------
        # STEP 6 — Report settings
        # -------------------------------------------------------------
        if payload.report_avenue_ids:
            project.report_avenues = db.query(ReportAvenue).filter(
                ReportAvenue.id.in_(payload.report_avenue_ids)
            ).all()

        if payload.report_time_ids:
            project.report_times = db.query(ReportTime).filter(
                ReportTime.id.in_(payload.report_time_ids)
            ).all()

        if payload.report_consultation_ids:
            project.report_consultations = db.query(ReportConsultation).filter(
                ReportConsultation.id.in_(payload.report_consultation_ids)
            ).all()

        # -------------------------------------------------------------
        # FINAL COMMIT
        # -------------------------------------------------------------
        db.commit()
        db.refresh(project)

        return ProjectOutSafe.from_model(project)

    except Exception:
        db.rollback()
        raise


# -------------------------------------------------------
# GET ALL PROJECTS (SAFE OUTPUT)
# -------------------------------------------------------
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
    ])),
):

    query = db.query(Project).filter(Project.is_deleted == False)

    # ------------------------------
    # Filters
    # ------------------------------
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

    # ------------------------------
    # Pagination
    # ------------------------------
    total = query.count()

    skip = (page - 1) * page_size
    items = query.offset(skip).limit(page_size).all()

    # ------------------------------
    # Safe serialization
    # ------------------------------
    results = [ProjectOutSafe.from_model(p) for p in items]

    base_url = str(request.url).split("?")[0]

    next_url = None
    prev_url = None

    if skip + page_size < total:
        next_url = f"{base_url}?page={page+1}&page_size={page_size}"

    if page > 1:
        prev_url = f"{base_url}?page={page-1}&page_size={page_size}"

    return {
        "count": total,
        "next": next_url,
        "previous": prev_url,
        "results": results
    }


# -------------------------------------------------------
# GET SINGLE PROJECT (SAFE OUTPUT)
# -------------------------------------------------------
@router.get("/{uid}/", response_model=ProjectOutSafe)
def get_project(
    uid: str,
    db: Session = Depends(get_db),
    current_user=Depends(
        require_role([
            UserRole.super_admin,
            UserRole.org_admin,
            UserRole.reviewer,
            UserRole.data_clerk,
            UserRole.org_user
        ])
    ),
):

    project = db.query(Project).filter(
        Project.id == uid,
        Project.is_deleted == False
    ).first()

    if not project:
        raise HTTPException(404, "Project not found")

    return ProjectOutSafe.from_model(project)



# -------------------------------------------------------
# GET PROJECT PROGRESS LOGS
# -------------------------------------------------------
@router.get("/{uid}/progress/", response_model=List[ProjectProgressOut])
def get_project_progress(
    uid: str,
    db: Session = Depends(get_db),
    current_user=Depends(
        require_role([
            UserRole.super_admin,
            UserRole.org_admin,
            UserRole.reviewer,
            UserRole.data_clerk,
            UserRole.org_user
        ])
    ),
):
    # Ensure the project exists
    project = db.query(Project).filter(
        Project.id == uid,
        Project.is_deleted == False
    ).first()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Get progress ordered by creation time
    progress_logs = db.query(ProjectProgress).filter(
        ProjectProgress.project_id == uid
    ).order_by(ProjectProgress.created_at.asc()).all()

    return [ProjectProgressOut.from_orm(p) for p in progress_logs]



# -------------------------------------------------------
# UPDATE PROJECT (FULL SAFE)
# -------------------------------------------------------
@router.put("/{uid}/", response_model=ProjectOutSafe)
def update_project(
    uid: str,
    payload: ProjectUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(
        require_role([
            UserRole.super_admin,
            UserRole.org_admin,
        ])
    ),
):
    project = db.query(Project).filter(
        Project.id == uid,
        Project.is_deleted == False
    ).first()

    if not project:
        raise HTTPException(404, "Project not found")

    # ------------------------------------------------
    # Basic fields
    # ------------------------------------------------
    update_data = payload.model_dump(exclude_unset=True)

    if "title" in update_data:
        project.title = update_data["title"]

    if "description" in update_data:
        project.description = update_data["description"]

    # ------------------------------------------------
    # Categories
    # ------------------------------------------------
    if payload.category_ids is not None:
        project.categories = db.query(ProjectCategory).filter(
            ProjectCategory.id.in_(payload.category_ids)
        ).all()

    # ------------------------------------------------
    # Collaborators
    # ------------------------------------------------
    if payload.collaborator_ids is not None:
        project.collaborators = db.query(ClientUser).filter(
            ClientUser.id.in_(payload.collaborator_ids)
        ).all()

    # ------------------------------------------------
    # Media sources (clear and repopulate)
    # ------------------------------------------------
    if payload.media_source_ids is not None:
        # Delete old
        db.query(ProjectMediaSources).filter(
            ProjectMediaSources.project_id == project.id
        ).delete()
        db.commit()

        # Insert new
        for ms_id in payload.media_source_ids:
            db.add(ProjectMediaSources(
                project_id=project.id,
                media_source_id=ms_id
            ))

    # ------------------------------------------------
    # Report Avenues
    # ------------------------------------------------
    if payload.report_avenue_ids is not None:
        project.report_avenues = db.query(ReportAvenue).filter(
            ReportAvenue.id.in_(payload.report_avenue_ids)
        ).all()

    if payload.report_time_ids is not None:
        project.report_times = db.query(ReportTime).filter(
            ReportTime.id.in_(payload.report_time_ids)
        ).all()

    if payload.report_consultation_ids is not None:
        project.report_consultations = db.query(ReportConsultation).filter(
            ReportConsultation.id.in_(payload.report_consultation_ids)
        ).all()

    db.commit()
    db.refresh(project)

    return ProjectOutSafe.from_model(project)


# -------------------------------------------------------
# UPDATE PROJECT STATUS WITH CONTROLLED TRANSITIONS
# -------------------------------------------------------
@router.patch("/{uid}/status/", response_model=ProjectOutSafe)
def update_project_status(
    uid: str,
    payload: ProjectStatusUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(
        require_role([
            UserRole.super_admin,
            UserRole.org_admin,
            UserRole.reviewer,
        ])
    ),
):

    # ------------------------------------
    # 1. Fetch project
    # ------------------------------------
    project = db.query(Project).filter(
        Project.id == uid,
        Project.is_deleted == False
    ).first()

    if not project:
        raise HTTPException(404, "Project not found")

    previous_status = project.status.value
    new_status = payload.status.value

    # ------------------------------------
    # 2. Check transition rule
    # ------------------------------------
    allowed_next = ALLOWED_STATUS_TRANSITIONS.get(previous_status, set())

    if new_status not in allowed_next:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Invalid status transition: {previous_status} → {new_status}. "
                f"Allowed transitions: {', '.join(allowed_next) or 'none'}"
            )
        )

    # ------------------------------------
    # 3. Update project status
    # ------------------------------------
    project.status = payload.status
    db.flush()  # Ensure project status is updated before logging progress

    # ------------------------------------
    # 4. Log status transition in PROJECT_PROGRESS
    # ------------------------------------
    last_stage = db.query(ProjectProgress).filter(
        ProjectProgress.project_id == project.id
    ).order_by(ProjectProgress.stage_no.desc()).first()

    next_stage_no = (last_stage.stage_no + 1) if last_stage else 1

    progress_entry = ProjectProgress(
        project_id=project.id,
        stage_no=next_stage_no,
        owner_id=current_user["id"],
        previous_status=previous_status,
        current_status=new_status,
        action=payload.action,
        comment=payload.comment
    )

    db.add(progress_entry)
    db.commit()
    db.refresh(project)

    return ProjectOutSafe.from_model(project)

# -------------------------------------------------------
# DELETE PROJECT (SOFT DELETE)
# -------------------------------------------------------
@router.delete("/{uid}/", status_code=204)
def delete_project(
    uid: str,
    db: Session = Depends(get_db),
    current_user=Depends(
        require_role([
            UserRole.super_admin,
            UserRole.org_admin,
        ])
    ),
):

    project = db.query(Project).filter(
        Project.id == uid,
        Project.is_deleted == False
    ).first()

    if not project:
        raise HTTPException(404, "Project not found")

    # Soft delete the main project
    project.is_deleted = True

    # Soft delete media source links
    db.query(ProjectMediaSources).filter(
        ProjectMediaSources.project_id == project.id
    ).update({"is_deleted": True})

    # NOTE:
    # Thematic areas created specifically for this project are new rows,
    # so they are safe to soft delete.
    for ta in project.thematic_areas:
        ta.is_deleted = True

    db.commit()

    return None



