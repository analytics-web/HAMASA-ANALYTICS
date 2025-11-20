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

router = APIRouter(prefix="/projects", tags=["Project Machine Learning"])

#-----------------------------------
# Get Project Details Needed for ML
#-----------------------------------
@router.get("/{uid}/ml-details/", response_model=ProjectMLDetailsOut)
def get_project_ml_details(
    uid: UUID4,
    db: Session = Depends(get_db),
    current_user=Depends(require_role([
        UserRole.super_admin,
        UserRole.reviewer,
    ]))
):
    project = db.query(Project).filter(Project.id == uid).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    return ProjectMLDetailsOut(
        id=project.id,
        title=project.title,
        thematic_areas=[ta.area for ta in project.thematic_areas],
        media_sources=[ms.name for ms in project.media_sources],
    )


# -----------------------------------
# Project ML Analysis Results
# -----------------------------------
@router.post("/ml-csv-url", response_model=MLCSVStoredResponse,
             dependencies=[Depends(require_role([
                 UserRole.super_admin,
                 UserRole.reviewer,
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
@router.get("/{uid}/ml-results")
def get_ml_results(
    uid: UUID4,
    db: Session = Depends(get_db),
    current_user=Depends(require_role([
        UserRole.super_admin,
        UserRole.reviewer,
    ]))
):
    results = (
        db.query(MLAnalysisResult)
        .filter(MLAnalysisResult.uid == uid)
        .order_by(MLAnalysisResult.row_number)
        .all()
    )

    return [r.data for r in results]
