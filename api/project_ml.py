import csv
from io import StringIO
from fastapi import APIRouter, Depends, HTTPException, Request, requests, status
from sqlalchemy.orm import Session
from typing import List
from api.deps import require_role
from models.ml_analysis_result import MLAnalysisResult
from models.project import Project
from schemas.client import PaginatedResponse
from schemas.hamasa_user import UserRole
from schemas.project import *
from db import get_db
from utils.pagination import paginate_queryset

router = APIRouter(prefix="/projects/projects_ml", tags=["Project Machine Learning"])


# -------------------------------------------------------
# GET ALL PROJECTS THAT ARE ACTIVE FOR ANALYTICS
# -------------------------------------------------------
@router.get("/", response_model=PaginatedResponse, dependencies=[Depends(require_role([
                 UserRole.super_admin,
                 UserRole.reviewer,
                 UserRole.ml_service
             ]))])
def get_active_projects(
    request: Request,
    filters: ProjectFilters = Depends(),
    page: int = 1,
    page_size: int = 10,
    db: Session = Depends(get_db),
):

    query = db.query(Project).filter(Project.is_deleted == False, Project.status == ProjectStatus.active)

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



# -----------------------------------
# Project ML Analysis Results
# -----------------------------------
@router.post("/ml-csv-url", response_model=MLCSVStoredResponse,
             dependencies=[Depends(require_role([
                 UserRole.super_admin,
                 UserRole.reviewer,
                 UserRole.ml_service
             ]))])
def process_ml_csv(
    payload: MLCSVRequest,
    db: Session = Depends(get_db)
):
    project = db.query(Project).filter(Project.id == payload.uid).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # 1. Download CSV
    try:
        response = requests.get(payload.csv_url, timeout=10)
        response.raise_for_status()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to download CSV: {e}")

    # 2. Parse CSV
    csv_text = response.text
    reader = csv.DictReader(StringIO(csv_text))
    rows = list(reader)

    if not rows:
        raise HTTPException(status_code=400, detail="CSV is empty")

    # 3. Clear previous ML results for this project
    db.query(MLAnalysisResult).filter(
        MLAnalysisResult.uid == project.id
    ).delete()

    # 4. Insert results
    for i, row in enumerate(rows):
        ml_row = MLAnalysisResult(
            uid=project.id,
            row_number=i + 1,
            data=row
        )
        db.add(ml_row)

    db.commit()

    return MLCSVStoredResponse(
        uid=project.id,
        total_rows=len(rows),
    )


# -----------------------------------
# Get Project ML Analysis Results
# -----------------------------------
# @router.get("/{uid}/ml-results")
# def get_ml_results(
#     uid: UUID4,
#     db: Session = Depends(get_db),
#     current_user=Depends(require_role([
#         UserRole.super_admin,
#         UserRole.reviewer,
#     ]))
# ):
#     results = (
#         db.query(MLAnalysisResult)
#         .filter(MLAnalysisResult.uid == uid)
#         .order_by(MLAnalysisResult.row_number)
#         .all()
#     )

#     return [r.data for r in results]
