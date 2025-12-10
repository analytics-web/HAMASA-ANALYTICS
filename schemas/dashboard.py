import datetime
import json
import uuid
from pydantic import BaseModel, UUID4, Field
from typing import List, Optional

from models.enums import ProjectMediaCategory, ProjectStatus
from models.project import MediaSource, Project, ProjectThematicAreas
from datetime import datetime


class DashboardSummary(BaseModel):
    total_clients: int
    total_projects: int
    active_projects: int
    total_media_sources: int



class MediaSourceCoverage(BaseModel):
    name: str
    coverage_percent: float
    source_count: int



class RecentReport(BaseModel):
    client_name: str
    title: str
    source:str
    date: datetime
    status: str



class MediaMonitoringItem(BaseModel):
    category: str   # TV, Print, Radio, Social, etc.
    daily: int
    weekly: int
    monthly: int


class ReportStatusSummary(BaseModel):
    verified: int
    unverified: int
    rejected: int


class DashboardResponse(BaseModel):
    summary: DashboardSummary
    media_coverage: List[MediaSourceCoverage]
    recent_reports: List[RecentReport]
    monitoring: List[MediaMonitoringItem]
    report_status_summary: ReportStatusSummary
