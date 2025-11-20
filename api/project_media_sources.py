import csv
from io import StringIO
from uuid import UUID
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
from utils.project_helpers import get_category_by_name

router = APIRouter(prefix="/projects", tags=["Project Media Categories"])

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
    # Get category by name (enum value)
    category = db.query(MediaCategory).filter(
        MediaCategory.name.ilike(source.category_name.value),
        MediaCategory.is_deleted == False,
    ).first()

    if not category:
        raise HTTPException(404, f"Media category '{source.category_name}' not found")

    # Check duplicates
    exists = db.query(MediaSource).filter(
        MediaSource.name.ilike(source.name),
        MediaSource.category_id == category.id,
        MediaSource.is_deleted == False
    ).first()

    if exists:
        raise HTTPException(400, "Media source already exists in this category")

    new_source = MediaSource(
        name=source.name.strip(),
        category_id=category.id
    )

    db.add(new_source)
    db.commit()
    db.refresh(new_source)

    return MediaSourceOut(
        id=new_source.id,
        name=new_source.name,
        category_name=category.name
    )


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
    query = (
        db.query(
            MediaSource.id,
            MediaSource.name,
            MediaCategory.name.label("category_name")
        )
        .join(MediaCategory, MediaCategory.id == MediaSource.category_id)
        .filter(MediaSource.is_deleted == False)
    )

    # Filter by category ID
    if filters.category_id:
        query = query.filter(MediaSource.category_id == filters.category_id)

    # Filter by category name (via enum or raw string)
    if filters.search:
        query = query.filter(MediaSource.name.ilike(f"%{filters.search}%"))

    # Sort safely
    sort_field = {
        "name": MediaSource.name,
        "created_at": MediaSource.created_at,
        "category_name": MediaCategory.name
    }.get(filters.sort_by, MediaSource.created_at)

    query = query.order_by(
        sort_field.asc() if filters.sort_order.lower() == "asc" else sort_field.desc()
    )

    base_url = str(request.url).split("?")[0]

    return paginate_queryset(query, page, page_size, base_url, MediaSourceOut)




#------------------------------
# update media source
#------------------------------
@router.patch("/media-sources/{id}", response_model=MediaSourceOut)
def update_media_source(
    id: UUID,
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

    # Category update using enum name
    if "category_id" not in update_data and "category_name" in update_data:
        category = db.query(MediaCategory).filter(
            MediaCategory.name.ilike(update_data["category_name"]),
            MediaCategory.is_deleted == False
        ).first()

        if not category:
            raise HTTPException(404, "New category not found")

        update_data["category_id"] = category.id

    # Duplicate prevention
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

    for field, value in update_data.items():
        setattr(source, field, value)

    db.commit()
    db.refresh(source)

    category = db.query(MediaCategory).filter(MediaCategory.id == source.category_id).first()

    return MediaSourceOut(
        id=source.id,
        name=source.name,
        category_name=category.name
    )


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

