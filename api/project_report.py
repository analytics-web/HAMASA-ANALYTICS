from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from models.project import Project
from models.project_report import ProjectReport
from models.project_progress import ProjectProgress
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



@router.post("/{project_id}/reports", response_model=ProjectReportOut)
def create_report(
    project_id: str,
    data: ProjectReportCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_role([
        UserRole.super_admin, UserRole.org_admin,
        UserRole.reviewer, UserRole.data_clerk
    ]))
):
    project = db.query(Project).filter(
        Project.id == project_id, Project.is_deleted == False
    ).first()

    if not project:
        raise HTTPException(404, "Project not found")

    report = ProjectReport(
        project_id=project_id,
        **data.dict(),
        status="Unverified"
    )

    db.add(report)
    db.commit()
    db.refresh(report)

    return report



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
