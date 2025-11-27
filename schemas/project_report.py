from pydantic import BaseModel, UUID4
from datetime import datetime
from typing import Optional, List, Any


class ProjectReportBase(BaseModel):
    publication_date: datetime
    title: str
    content: Optional[str] = None
    source: Optional[str] = None
    media_category: Optional[str] = None
    media_format: Optional[str] = None
    thematic_area: Optional[str] = None
    thematic_description: Optional[str] = None
    objectives: Optional[List[Any]] = None
    link: Optional[str] = None


class ProjectReportCreate(ProjectReportBase):
    pass


class ProjectReportUpdate(BaseModel):
    publication_date: Optional[datetime] = None
    title: Optional[str] = None
    content: Optional[str] = None
    source: Optional[str] = None
    media_category: Optional[str] = None
    media_format: Optional[str] = None
    thematic_area: Optional[str] = None
    thematic_description: Optional[str] = None
    objectives: Optional[List[Any]] = None
    link: Optional[str] = None


class ProjectReportOut(ProjectReportBase):
    id: UUID4
    status: Optional[str]
    extra_metadata: Optional[Any]
    
    class Config:
        from_attributes = True


class ProjectReportStatusUpdate(BaseModel):
    status: str
    comment: Optional[str] = None
