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

router = APIRouter(prefix="/projects", tags=["Project Media Sources"])

#--------------------------------------------------------------------------------------------------
# ---------------------------- Project-Media-Sources CRUD Operations ----------------------------------
#--------------------------------------------------------------------------------------------------


#-------------------
# Media Create Sources
#-------------------
@router.post("/media-sources/", response_model=MediaSourceOut)
def create_media_source(
    source: MediaSourceBase,
    current_user=Depends(require_role([
        UserRole.super_admin,
        UserRole.org_admin,
        UserRole.reviewer,
        UserRole.data_clerk,
        UserRole.org_user
    ])),
    db: Session = Depends(get_db)
):
    # Ensure category exists
    category = db.query(MediaCategory).filter(
        MediaCategory.id == source.category_id,
        MediaCategory.is_deleted == False
    ).first()

    if not category:
        raise HTTPException(404, "Media category not found")

    # Prevent duplicate name inside the same category
    exists = db.query(MediaSource).filter(
        MediaSource.name.ilike(source.name),
        MediaSource.category_id == source.category_id,
        MediaSource.is_deleted == False
    ).first()

    if exists:
        raise HTTPException(400, "Media source already exists in this category")

    new_source = MediaSource(
        name=source.name.strip(),
        category_id=source.category_id
    )

    db.add(new_source)
    db.commit()
    db.refresh(new_source)

    return new_source

#------------------------------
# get all media sources
#------------------------------
@router.get("/media-sources/", response_model=PaginatedResponse)
def get_media_sources(
    request: Request,
    filters: MediaSourceFilters = Depends(),
    page: int = 1,
    page_size: int = 10,
    db: Session = Depends(get_db)
):
    query = db.query(MediaSource).filter(MediaSource.is_deleted == False)

    # Filter by category
    if filters.category_id:
        query = query.filter(MediaSource.category_id == filters.category_id)

    # Search by name
    if filters.search:
        search = f"%{filters.search}%"
        query = query.filter(MediaSource.name.ilike(search))

    # Sorting
    sort_field = getattr(MediaSource, filters.sort_by, MediaSource.created_at)
    query = query.order_by(
        sort_field.asc() if filters.sort_order.lower() == "asc" else sort_field.desc()
    )

    base_url = str(request.url).split("?")[0]

    return paginate_queryset(query, page, page_size, base_url, MediaSourceOut)


#------------------------------
# get media source by id
#------------------------------
@router.get("/media-sources/{id}", response_model=MediaSourceOut)
def get_media_source(id: uuid.UUID, db: Session = Depends(get_db)):
    source = db.query(MediaSource).filter(
        MediaSource.id == id,
        MediaSource.is_deleted == False
    ).first()

    if not source:
        raise HTTPException(404, "Media source not found")

    return source

#------------------------------
# update media source
#------------------------------
@router.patch("/media-sources/{id}", response_model=MediaSourceOut)
def update_media_source(
    id: uuid.UUID,
    data: MediaSourceUpdate,
    current_user=Depends(require_role([
        UserRole.super_admin,
        UserRole.org_admin,
        UserRole.reviewer
    ])),
    db: Session = Depends(get_db)
):
    source = db.query(MediaSource).filter(
        MediaSource.id == id,
        MediaSource.is_deleted == False
    ).first()

    if not source:
        raise HTTPException(404, "Media source not found")

    update_data = data.model_dump(exclude_unset=True)

    # If category is being changed, verify it exists
    if "category_id" in update_data:
        category = db.query(MediaCategory).filter(
            MediaCategory.id == update_data["category_id"],
            MediaCategory.is_deleted == False
        ).first()

        if not category:
            raise HTTPException(404, "New category not found")

    # Prevent duplicates inside the same category
    if "name" in update_data or "category_id" in update_data:
        name = update_data.get("name", source.name)
        category_id = update_data.get("category_id", source.category_id)

        exists = db.query(MediaSource).filter(
            MediaSource.name.ilike(name),
            MediaSource.category_id == category_id,
            MediaSource.id != id,
            MediaSource.is_deleted == False
        ).first()

        if exists:
            raise HTTPException(400, "Another source with that name already exists in this category")

    # Apply updates
    for field, value in update_data.items():
        setattr(source, field, value)

    db.commit()
    db.refresh(source)

    return source


#------------------------------
# delete media source
#------------------------------
@router.delete("/media-sources/{id}", status_code=204)
def delete_media_source(
    id: uuid.UUID,
    current_user=Depends(require_role([UserRole.super_admin])),
    db: Session = Depends(get_db)
):
    source = db.query(MediaSource).filter(
        MediaSource.id == id,
        MediaSource.is_deleted == False
    ).first()

    if not source:
        raise HTTPException(404, "Media source not found")

    source.is_deleted = True
    db.commit()
    return

