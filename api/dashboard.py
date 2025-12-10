from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.deps import require_role
from db import get_db
from models.client import Client
from models.enums import ProjectStatus, UserRole
from models.project_report import ProjectReport
from schemas.dashboard import DashboardResponse, DashboardSummary, MediaMonitoringItem, MediaSourceCoverage, RecentReport, ReportStatusSummary

from models.project import (
    MediaCategory,
    Project,
    ProjectMediaSources,
    MediaSource,
)


router = APIRouter(prefix="/dashboards", tags=["Dashboard"])



#----------------------------------------------
# Admin Dashboard
#----------------------------------------------
@router.get("/dashboard/overview/", response_model=DashboardResponse)
def get_dashboard_overview(
    db: Session = Depends(get_db),
    current_user=Depends(require_role([
        UserRole.super_admin,
        UserRole.reviewer,
        UserRole.data_clerk
    ]))
):
    # ---------- SUMMARY ----------
    total_clients = db.query(Client).filter(Client.is_deleted == False).count()
    total_projects = db.query(Project).filter(Project.is_deleted == False).count()
    active_projects = db.query(Project).filter(
        Project.status == ProjectStatus.active,
        Project.is_deleted == False
    ).count()
    total_media_sources = db.query(MediaSource).count()

    summary = DashboardSummary(
        total_clients=total_clients,
        total_projects=total_projects,
        active_projects=active_projects,
        total_media_sources=total_media_sources
    )

    # ---------- MEDIA SOURCE COVERAGE ----------
    coverage = []
    categories = db.query(MediaCategory).all()

    for cat in categories:
        total_cat_sources = len(cat.name)
        used_sources = (
            db.query(ProjectMediaSources)
              .join(MediaSource)
              .filter(MediaSource.category_id == cat.id)
              .count()
        )

        coverage_percent = (used_sources / total_cat_sources * 100) if total_cat_sources > 0 else 0

        coverage.append(MediaSourceCoverage(
            name=cat.name,
            coverage_percent=round(coverage_percent, 2),
            source_count=used_sources
        ))

    # ---------- RECENT REPORTS ----------
    recent_raw = (
        db.query(ProjectReport)
        .order_by(ProjectReport.publication_date.desc())
        .limit(5)
        .all()
    )

    recent_reports = []
    for r in recent_raw:
        recent_reports.append(RecentReport(
            client_name=r.project.client.name_of_organisation,
            title=r.title,
            date=r.publication_date,
            status=r.status
        ))

    # ---------- MONITORING ----------
    monitoring = []
    categories = ["Print Media", "TV", "Radio", "Social Media"]

    for cat in categories:
        monitoring.append(MediaMonitoringItem(
            category=cat,
            daily=db.query(ProjectReport).filter(ProjectReport.media_category == cat).count(),
            weekly=db.query(ProjectReport).filter(ProjectReport.media_category == cat).count(),
            monthly=db.query(ProjectReport).filter(ProjectReport.media_category == cat).count(),
        ))

    # ---------- REPORT STATUS ----------
    status_summary = ReportStatusSummary(
        verified=db.query(ProjectReport).filter(ProjectReport.status == "Verified").count(),
        unverified=db.query(ProjectReport).filter(ProjectReport.status == "Unverified").count(),
        rejected=db.query(ProjectReport).filter(ProjectReport.status == "Rejected").count(),
    )

    return DashboardResponse(
        summary=summary,
        media_coverage=coverage,
        recent_reports=recent_reports,
        monitoring=monitoring,
        report_status_summary=status_summary
    )
