import uuid
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import func

from api.deps import require_role
from db import get_db
from utils.pagination import paginate_queryset_list

from schemas.hamasa_user import UserRole
from schemas.project import (
    MediaSourceBase,
    MediaSourceOut,
    MediaSourceFilters,
    MediaSourceUpdate,
)
from models.project import MediaCategory, MediaSource
from models.enums import ProjectMediaCategory


router = APIRouter(prefix="/projects", tags=["Project Media Sources"])


# ------------------------------------------------------------------
# CATEGORY MAPPING LOGIC
# ------------------------------------------------------------------

# Enum value → DB name
ENUM_TO_DB = {
    ProjectMediaCategory.social_media: "Social Media",
    ProjectMediaCategory.radio: "Radio",
    ProjectMediaCategory.tv: "TV",
    ProjectMediaCategory.print_media: "Print Media",
    ProjectMediaCategory.online_media: "Online Media",
    ProjectMediaCategory.others: "Others",
}

# DB name → Enum
DB_TO_ENUM = {v.lower(): k for k, v in ENUM_TO_DB.items()}


def normalize_category(db_value: str) -> ProjectMediaCategory:
    """Convert DB string to enum safely."""
    if not db_value:
        return ProjectMediaCategory.others

    key = db_value.strip().lower()
    return DB_TO_ENUM.get(key, ProjectMediaCategory.others)


# ------------------------------------------------------------------
# CREATE MEDIA SOURCE
# ------------------------------------------------------------------
@router.post("/media-sources/", response_model=MediaSourceOut)
@router.post("/media-sources/", response_model=MediaSourceOut)
def create_media_source(
    source: MediaSourceBase,
    current_user=Depends(require_role([
        UserRole.super_admin,
        UserRole.org_admin,
        UserRole.reviewer,
        UserRole.data_clerk,
        UserRole.org_user,
    ])),
    db: Session = Depends(get_db),
):
    # Enum → actual string (already matches DB)
    db_category_name = source.category_name.value

    # Find category by name (case-insensitive)
    category = db.query(MediaCategory).filter(
        func.lower(MediaCategory.name) == func.lower(db_category_name),
        MediaCategory.is_deleted == False
    ).first()

    if not category:
        raise HTTPException(
            404,
            f"Media category '{db_category_name}' not found in database"
        )

    # Duplicate name check
    exists = db.query(MediaSource).filter(
        func.lower(MediaSource.name) == func.lower(source.name),
        MediaSource.category_id == category.id,
        MediaSource.is_deleted == False
    ).first()

    if exists:
        raise HTTPException(
            400,
            "Media source already exists in this category"
        )

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
        category_name=source.category_name
    )


# ------------------------------------------------------------------
# GET ALL MEDIA SOURCES
# ------------------------------------------------------------------
@router.get("/media-sources/", response_model=dict)
def get_media_sources(
    request: Request,
    filters: MediaSourceFilters = Depends(),
    page: int = 1,
    page_size: int = 10,
    db: Session = Depends(get_db),
):

    query = (
        db.query(
            MediaSource.id,
            MediaSource.name,
            MediaCategory.name.label("category_name"),
        )
        .join(MediaCategory, MediaCategory.id == MediaSource.category_id)
        .filter(MediaSource.is_deleted == False)
    )

    # Filter by category ID
    if filters.category_id:
        query = query.filter(MediaSource.category_id == filters.category_id)

    # Search by name
    if filters.name:
        query = query.filter(MediaSource.name.ilike(f"%{filters.name}%"))

    # Sorting
    sort_field = {
        "name": MediaSource.name,
        "created_at": MediaSource.created_at,
        "category_name": MediaCategory.name,
    }.get(filters.sort_by, MediaSource.created_at)

    query = query.order_by(
        sort_field.asc() if filters.sort_order.lower() == "asc"
        else sort_field.desc()
    )

    rows = query.all()
    results = [
        MediaSourceOut(
            id=r.id,
            name=r.name,
            category_name=normalize_category(r.category_name),
        )
        for r in rows
    ]

    base_url = str(request.url).split("?")[0]

    return paginate_queryset_list(results, page, page_size, base_url)

#-------------------------------------------------------------------
# Get MEDIA SOURCE by ID
#-------------------------------------------------------------------
@router.get("/media-sources/{id}", response_model=MediaSourceOut)
def get_media_source(
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
    item = db.query(MediaSource).filter(
        MediaSource.id == id,
        MediaSource.is_deleted == False
    ).first()

    if not item:
        raise HTTPException(404, "Media source not found")

    return MediaSourceOut(
        id=item.id,
        name=item.name,
        category_name=ProjectMediaCategory(item.category.name)
    )



# ------------------------------------------------------------------
# UPDATE MEDIA SOURCE
# ------------------------------------------------------------------
@router.patch("/media-sources/{id}", response_model=MediaSourceOut)
def update_media_source(
    id: uuid.UUID,
    data: MediaSourceUpdate,
    current_user=Depends(require_role([
        UserRole.super_admin,
        UserRole.org_admin,
        UserRole.reviewer,
    ])),
    db: Session = Depends(get_db),
):

    source = db.query(MediaSource).filter(
        MediaSource.id == id,
        MediaSource.is_deleted == False,
    ).first()

    if not source:
        raise HTTPException(404, "Media source not found")

    update_data = data.model_dump(exclude_unset=True)

    # Handle category change via enum
    if "category_name" in update_data:
        db_name = ENUM_TO_DB[update_data["category_name"]]

        category = db.query(MediaCategory).filter(
            func.lower(MediaCategory.name) == func.lower(db_name),
            MediaCategory.is_deleted == False,
        ).first()

        if not category:
            raise HTTPException(404, "New category not found")

        update_data["category_id"] = category.id
        update_data.pop("category_name", None)

    # Duplicate check
    new_name = update_data.get("name", source.name)
    new_category_id = update_data.get("category_id", source.category_id)

    exists = db.query(MediaSource).filter(
        func.lower(MediaSource.name) == func.lower(new_name),
        MediaSource.category_id == new_category_id,
        MediaSource.id != id,
        MediaSource.is_deleted == False,
    ).first()

    if exists:
        raise HTTPException(400, "Another source with that name already exists")

    # Apply update
    for key, value in update_data.items():
        setattr(source, key, value)

    db.commit()
    db.refresh(source)

    # Convert final DB category → enum
    category = db.query(MediaCategory).filter(MediaCategory.id == source.category_id).first()

    return MediaSourceOut(
        id=source.id,
        name=source.name,
        category_name=normalize_category(category.name),
    )


# ------------------------------------------------------------------
# DELETE MEDIA SOURCE
# ------------------------------------------------------------------
@router.delete("/media-sources/{id}", status_code=204)
def delete_media_source(
    id: uuid.UUID,
    current_user=Depends(require_role([UserRole.super_admin])),
    db: Session = Depends(get_db),
):

    source = db.query(MediaSource).filter(
        MediaSource.id == id,
        MediaSource.is_deleted == False,
    ).first()

    if not source:
        raise HTTPException(404, "Media source not found")

    source.is_deleted = True
    db.commit()
    return
