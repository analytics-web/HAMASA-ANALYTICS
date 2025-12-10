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

router = APIRouter(prefix="/projects", tags=["Project Collaborators"])

#--------------------------------------------------------------------------------------------------
# ---------------------------- Project-Collaborator CRUD Operations -------------------------------
#--------------------------------------------------------------------------------------------------


#--------------------------------
# Assign collaborator to project
#--------------------------------
@router.post("/{project_id}/collaborators/{user_id}/", response_model=ProjectOut)
def add_collaborator(
    project_id: uuid.UUID,
    user_id: uuid.UUID,
    current_user=Depends(require_role([UserRole.super_admin, UserRole.org_admin])),
    db: Session = Depends(get_db)
):
    # Fetch project
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.is_deleted == False
    ).first()

    if not project:
        raise HTTPException(404, "Project not found")

    # Fetch user
    user = db.query(ClientUser).filter(
        ClientUser.id == user_id,
        ClientUser.is_deleted == False
    ).first()

    if not user:
        raise HTTPException(404, "User not found")

    # Org Admins can only modify collaborators for their own client
    if current_user["role"] == UserRole.org_admin:
        if str(current_user["client_id"]) != str(project.client_id):
            raise HTTPException(403, "You cannot modify another organisation's project")
        if str(user.client_id) != str(project.client_id):
            raise HTTPException(403, "Collaborator does not belong to your organisation")

    # Prevent duplicates
    if user in project.collaborators:
        raise HTTPException(400, "Collaborator already assigned to this project")

    # Add collaborator
    project.collaborators.append(user)
    db.commit()
    db.refresh(project)

    return project


#--------------------------------
# Remove collaborator from project
#--------------------------------
@router.delete("/{project_id}/collaborators/{user_id}/", response_model=ProjectOut)
def remove_collaborator(
    project_id: uuid.UUID,
    user_id: uuid.UUID,
    current_user=Depends(require_role([UserRole.super_admin, UserRole.org_admin])),
    db: Session = Depends(get_db)
):
    # Fetch project
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.is_deleted == False
    ).first()

    if not project:
        raise HTTPException(404, "Project not found")

    # Fetch user
    user = db.query(ClientUser).filter(
        ClientUser.id == user_id,
        ClientUser.is_deleted == False
    ).first()

    if not user:
        raise HTTPException(404, "User not found")

    # Org Admins can only update users within their org
    if current_user["role"] == UserRole.org_admin:
        if str(current_user["client_id"]) != str(project.client_id):
            raise HTTPException(403, "You cannot modify another organisation's project")
        if str(user.client_id) != str(project.client_id):
            raise HTTPException(403, "User does not belong to your organisation")

    # Check assignment before removing
    if user not in project.collaborators:
        raise HTTPException(400, "Collaborator is not assigned to this project")

    project.collaborators.remove(user)
    db.commit()
    db.refresh(project)

    return project




