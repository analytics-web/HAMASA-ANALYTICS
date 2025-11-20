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

router = APIRouter(prefix="/projects", tags=["Project Categories"])


#--------------------------------------------------------------------------------------------------
# ---------------------------- Project-Category CRUD Operations ----------------------------------
#--------------------------------------------------------------------------------------------------

#----------------------------------------------
# Create Categories all admins and client admin
#----------------------------------------------
@router.post("/categories/", response_model=ProjectCategoryOut)
def create_category(
    category: ProjectCategoryCreate,
    current_user=Depends(require_role([
        UserRole.super_admin,
        UserRole.org_admin,
        UserRole.reviewer
    ])),
    db: Session = Depends(get_db),
):
    # Check if category exists
    existing = db.query(ProjectCategory).filter(
        ProjectCategory.category.ilike(category.category)
    ).first()

    if existing:
        raise HTTPException(
            status_code=400,
            detail="Category already exists"
        )

    new_cat = ProjectCategory(
        category=category.name.strip(),
        description=category.description.strip()
    )

    db.add(new_cat)
    db.commit()
    db.refresh(new_cat)
    return new_cat


#------------------------------
# get all categories
#------------------------------
@router.get("/categories/", response_model=PaginatedResponse )
def get_categories(
    request: Request,
    filters: CategoryFilters = Depends(),
    page: int = 1,
    page_size: int = 10,
    db: Session = Depends(get_db)
):
    query = db.query(ProjectCategory).filter(ProjectCategory.is_deleted == False)

    # Search filter
    if filters.search:
        query = query.filter(
            ProjectCategory.category.ilike(f"%{filters.search}%")
        )

    # Sorting
    sort_field = getattr(ProjectCategory, filters.sort_by, ProjectCategory.created_at)
    if filters.sort_order.lower() == "asc":
        query = query.order_by(sort_field.asc())
    else:
        query = query.order_by(sort_field.desc())

    base_url = str(request.url).split("?")[0]

    return paginate_queryset(query, page, page_size, base_url, ProjectCategoryOut)


#------------------------------
# get category by id
#------------------------------
@router.get("/categories/{category_id}", response_model=ProjectCategoryOut)
def get_category(category_id: uuid.UUID, db: Session = Depends(get_db)):
    category = db.query(ProjectCategory).filter(
        ProjectCategory.id == category_id,
        ProjectCategory.is_deleted == False
    ).first()

    if not category:
        raise HTTPException(404, "Category not found")

    return category



#------------------------------
# update category
#------------------------------
@router.patch("/categories/{category_id}", response_model=ProjectCategoryOut)
def update_category(
    category_id: uuid.UUID,
    data: ProjectCategoryUpdate,
    current_user=Depends(require_role([UserRole.super_admin, UserRole.org_admin])),
    db: Session = Depends(get_db),
):
    category = db.query(ProjectCategory).filter(
        ProjectCategory.id == category_id,
        ProjectCategory.is_deleted == False
    ).first()

    if not category:
        raise HTTPException(404, "Category not found")

    # Prevent duplicates
    if data.category:
        exists = db.query(ProjectCategory).filter(
            ProjectCategory.category.ilike(data.category),
            ProjectCategory.id != category_id
        ).first()

        if exists:
            raise HTTPException(400, "Another category with that name already exists")

        category.category = data.category.strip()

    db.commit()
    db.refresh(category)
    return category



#------------------------------
# delete category
#------------------------------
@router.delete("/categories/{category_id}", status_code=204)
def delete_category(
    category_id: uuid.UUID,
    current_user=Depends(require_role([UserRole.super_admin])),
    db: Session = Depends(get_db),
):
    category = db.query(ProjectCategory).filter(
        ProjectCategory.id == category_id,
        ProjectCategory.is_deleted == False
    ).first()

    if not category:
        raise HTTPException(404, "Category not found")

    category.is_deleted = True
    db.commit()
    return
