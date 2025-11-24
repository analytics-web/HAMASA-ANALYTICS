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

router = APIRouter(prefix="/projects", tags=["Project Media Categories"])


#--------------------------------------------------------------------------------------------------
# ---------------------------- Project-Media-Category CRUD Operations -----------------------------
#--------------------------------------------------------------------------------------------------


#------------------------------
# Media Create Categories
#------------------------------
@router.post("/media-categories/", response_model=MediaCategoryOut)
def create_media_category(
    category: MediaCategoryBase,
    current_user=Depends(require_role([
        UserRole.super_admin,
        UserRole.org_admin,
        UserRole.reviewer,
        UserRole.data_clerk,
        UserRole.org_user
    ])),
    db: Session = Depends(get_db)
):
    # Prevent duplicates
    exists = db.query(MediaCategory).filter(
        MediaCategory.name.ilike(category.name)
    ).first()

    if exists:
        raise HTTPException(400, "Media category already exists")

    new_cat = MediaCategory(
        name=category.name.strip(),
        description=category.description
    )

    db.add(new_cat)
    db.commit()
    db.refresh(new_cat)

    return new_cat


#------------------------------
# get all media categories
#------------------------------
@router.get("/media-categories/", response_model=PaginatedResponse)
def get_media_categories(
    request: Request,
    filters: MediaCategoryFilters = Depends(),
    page: int = 1,
    page_size: int = 10,
    db: Session = Depends(get_db)
):
    query = db.query(MediaCategory).filter(MediaCategory.is_deleted == False)

    # Search by name or description
    if filters.search:
        search = f"%{filters.search}%"
        query = query.filter(
            MediaCategory.name.ilike(search) |
            MediaCategory.description.ilike(search)
        )

    # Sorting
    sort_field = getattr(MediaCategory, filters.sort_by, MediaCategory.created_at)
    query = query.order_by(
        sort_field.asc() if filters.sort_order.lower() == "asc" else sort_field.desc()
    )

    base_url = str(request.url).split("?")[0]
    return paginate_queryset(query, page, page_size, base_url, MediaCategoryOut)


#------------------------------
# get media category by id
#------------------------------
@router.get("/media-categories/{id}", response_model=MediaCategoryOut)
def get_media_category(
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
    item = db.query(MediaCategory).filter(
        MediaCategory.id == id,
        MediaCategory.is_deleted == False
    ).first()

    if not item:
        raise HTTPException(404, "Media category not found")

    return item



#------------------------------
# update media category
#------------------------------
@router.patch("/media-categories/{id}", response_model=MediaCategoryOut, )
def update_media_category(
    id: uuid.UUID,
    data: MediaCategoryUpdate,
    current_user=Depends(require_role([
        UserRole.super_admin,
        UserRole.org_admin,
        UserRole.reviewer
    ])),
    db: Session = Depends(get_db)
):
    category = db.query(MediaCategory).filter(
        MediaCategory.id == id,
        MediaCategory.is_deleted == False
    ).first()

    if not category:
        raise HTTPException(404, "Media category not found")

    # Prevent duplicate category name
    if data.name:
        exists = db.query(MediaCategory).filter(
            MediaCategory.name == data.name ,
            MediaCategory.id != id
        ).first()
        if exists:
            raise HTTPException(400, "Another category with that name already exists")

    # Apply updates
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(category, field, value)

    db.commit()
    db.refresh(category)

    return category


#------------------------------
# delete media category
#------------------------------
@router.delete("/media-categories/{id}", status_code=204)
def delete_media_category(
    id: uuid.UUID,
    current_user=Depends(require_role([UserRole.super_admin])),
    db: Session = Depends(get_db)
):
    category = db.query(MediaCategory).filter(
        MediaCategory.id == id,
        MediaCategory.is_deleted == False
    ).first()

    if not category:
        raise HTTPException(404, "Media category not found")

    category.is_deleted = True
    db.commit()

    return

