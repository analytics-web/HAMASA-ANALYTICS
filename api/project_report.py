import requests
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from models.project import Project
from models.project_report import ProjectReport
from models.project_progress import ProjectProgress
from models.project_report_progress import ProjectReportProgress
from schemas.project_report import (
    ProjectReportCreate,
    ProjectReportUpdate,
    ProjectReportOut,
    ProjectReportStatusUpdate
)
from db import get_db
from models.enums import ProjectStatus
from api.deps import require_role
from models.enums import UserRole

router = APIRouter(prefix="/project", tags=["Project Reports"])



EXTERNAL_REPORT_URL = "https://hamasa-analytics-model.onrender.com/project/{project_id}/reports"


from datetime import datetime

@router.post("/{project_id}/reports/import")
def import_project_reports(
    project_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(require_role([
        UserRole.super_admin, UserRole.org_admin,
        UserRole.reviewer, UserRole.data_clerk
    ]))
):
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.is_deleted == False
    ).first()

    if not project:
        raise HTTPException(404, "Project not found")

    url = EXTERNAL_REPORT_URL.format(project_id=project_id)

    try:
        response = requests.get(url)
        response.raise_for_status()
    except Exception as e:
        raise HTTPException(500, f"Failed to fetch external reports: {e}")

    data = response.json()

    if "items" not in data:
        raise HTTPException(500, "Invalid external response format")

    items = data["items"]
    saved = 0

    for item in items:

        existing = db.query(ProjectReport).filter(
            ProjectReport.link == item.get("link"),
            ProjectReport.project_id == project_id
        ).first()

        if existing:
            continue

        # Convert date string to datetime
        raw_date = item.get("date")
        try:
            pub_date = datetime.strptime(raw_date, "%Y-%m-%d %H:%M:%S")
        except:
            raise HTTPException(500, f"Invalid date format: {raw_date}")

        report = ProjectReport(
            project_id=project_id,
            publication_date=pub_date,
            title=item.get("title"),
            content=item.get("content"),
            source=item.get("source"),
            media_category=item.get("media_category") or None,
            media_format=item.get("media_format"),
            thematic_area=item.get("thematic_area"),
            thematic_description=item.get("thematic_description"),
            objectives=item.get("objectives"),
            link=item.get("link"),
            status=item.get("status", "Unverified"),
            extra_metadata={}
        )

        db.add(report)
        saved += 1

    db.commit()

    return {
        "message": "Reports imported successfully",
        "project_id": project_id,
        "imported_count": saved,
        "total_received": len(items)
    }



@router.get("/{project_id}/reports", response_model=List[ProjectReportOut])
def list_reports(
    project_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(require_role([
        UserRole.super_admin, UserRole.org_admin,
        UserRole.reviewer, UserRole.data_clerk, UserRole.org_user
    ]))
):
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.is_deleted == False
    ).first()

    if not project:
        raise HTTPException(404, "Project not found")

    reports = db.query(ProjectReport).filter(
        ProjectReport.project_id == project_id
    ).order_by(ProjectReport.publication_date.desc()).all()

    return reports




@router.get("/report/{report_id}", response_model=ProjectReportOut)
def get_single_report(
    report_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(require_role([
        UserRole.super_admin, UserRole.org_admin,
        UserRole.reviewer, UserRole.data_clerk, UserRole.org_user
    ]))
):
    report = db.query(ProjectReport).filter(
        ProjectReport.id == report_id
    ).first()

    if not report:
        raise HTTPException(404, "Report not found")

    return report



@router.put("/report/{report_id}", response_model=ProjectReportOut)
def update_report(
    report_id: str,
    data: ProjectReportUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_role([
        UserRole.super_admin, UserRole.org_admin,
        UserRole.reviewer, UserRole.data_clerk
    ]))
):
    report = db.query(ProjectReport).filter(
        ProjectReport.id == report_id
    ).first()

    if not report:
        raise HTTPException(404, "Report not found")

    for key, value in data.dict(exclude_unset=True).items():
        setattr(report, key, value)

    db.commit()
    db.refresh(report)

    return report



@router.patch("/report/{report_id}/status")
def update_report_status(
    report_id: str,
    data: ProjectReportStatusUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_role([
        UserRole.super_admin, UserRole.org_admin,
        UserRole.reviewer
    ]))
):
    report = db.query(ProjectReport).filter(
        ProjectReport.id == report_id
    ).first()

    if not report:
        raise HTTPException(404, "Report not found")

    old_status = report.status
    report.status = data.status

    # Create progress log entry
    progress = ProjectReportProgress(
        project_id=report.project_id,
        stage_no=1,
        owner_id=current_user.id,
        previous_status=old_status,
        current_status=data.status,
        action="Status Update",
        comment=data.comment
)

    db.add(progress)
    db.commit()
    db.refresh(report)

    return {
        "message": "Status updated",
        "report_id": report_id,
        "old_status": old_status,
        "new_status": data.status
    }



@router.delete("/report/{report_id}")
def delete_report(
    report_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(require_role([
        UserRole.super_admin, UserRole.org_admin
    ]))
):
    report = db.query(ProjectReport).filter(
        ProjectReport.id == report_id
    ).first()

    if not report:
        raise HTTPException(404, "Report not found")

    db.delete(report)
    db.commit()

    return {"message": "Report deleted"}




  