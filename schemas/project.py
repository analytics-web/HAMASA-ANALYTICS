import uuid
from pydantic import BaseModel, UUID4, Field
from typing import List, Optional

from models.enums import ProjectStatus

class ProjectCategoryBase(BaseModel):
    category: str
    description: Optional[str] = None


class ProjectCategoryCreate(ProjectCategoryBase):
    pass

class ProjectCategoryOut(ProjectCategoryBase):
    id: UUID4
    class Config:
        from_attributes = True


class CategoryFilters(BaseModel):
    search: Optional[str] = None
    sort_by: Optional[str] = "created_at"
    sort_order: Optional[str] = "desc"  # asc or desc

class ProjectCategoryUpdate(BaseModel):
    category: Optional[str] = None
    description: Optional[str] = None


class ProjectThematicAreaBase(BaseModel):
    area: str
    title: str
    description: Optional[str] = None
    monitoring_objectives: List[str] 

class ProjectThematicAreaCreate(ProjectThematicAreaBase):
    pass

class ProjectThematicAreaOut(ProjectThematicAreaBase):
    id: UUID4
    class Config:
        from_attributes = True

class ProjectThematicAreaUpdate(BaseModel):
    area: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    monitoring_objectives: Optional[List[str]] = None

class ThematicAreaFilters(BaseModel):
    search: Optional[str] = None          # search in area/title/description
    sort_by: Optional[str] = "created_at" # default sort field
    sort_order: Optional[str] = "desc"    # asc or desc






class MediaCategoryBase(BaseModel):
    name: str

class MediaCategoryOut(MediaCategoryBase):
    id: UUID4
    media_sources: List["MediaSourceOut"] = []
    class Config:
        from_attributes = True

class MediaCategoryFilters(BaseModel):
    search: Optional[str] = None
    sort_by: Optional[str] = "created_at"
    sort_order: Optional[str] = "desc"


class MediaCategoryUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None




class MediaSourceBase(BaseModel):
    name: str
    category_id: UUID4

class MediaSourceOut(MediaSourceBase):
    id: UUID4
    class Config:
        from_attributes = True

class MediaSourceFilters(BaseModel):
    search: Optional[str] = None
    category_id: Optional[uuid.UUID] = None
    sort_by: Optional[str] = "created_at"
    sort_order: Optional[str] = "desc"


class MediaSourceUpdate(BaseModel):
    name: Optional[str] = None
    category_id: Optional[UUID4] = None










class ReportAvenueBase(BaseModel):
    name: str

class ReportAvenueCreate(ReportAvenueBase):
    pass

class ReportAvenueOut(ReportAvenueBase):
    id: UUID4
    class Config:
        from_attributes = True

class ReportAvenueFilters(BaseModel):
    search: Optional[str] = None
    sort_by: Optional[str] = "created_at"
    sort_order: Optional[str] = "desc"

class ReportAvenueUpdate(BaseModel):
    name: Optional[str] = None








class ReportTimeBase(BaseModel):
    name: str

class ReportTimeCreate(ReportTimeBase):
    pass

class ReportTimeOut(ReportTimeBase):
    id: UUID4
    class Config:
        from_attributes = True

class ReportTimeFilters(BaseModel):
    search: Optional[str] = None
    sort_by: Optional[str] = "created_at"
    sort_order: Optional[str] = "desc"

class ReportTimeUpdate(BaseModel):
    name: Optional[str] = None








class ReportConsultationBase(BaseModel):
    name: str

class ReportConsultationCreate(ReportConsultationBase):
    pass

class ReportConsultationOut(ReportConsultationBase):
    id: UUID4
    class Config:
        from_attributes = True

class ReportConsultationFilters(BaseModel):
    search: Optional[str] = None
    sort_by: Optional[str] = "created_at"
    sort_order: Optional[str] = "desc"

class ReportConsultationUpdate(BaseModel):
    name: Optional[str] = None










class ClientUserBase(BaseModel):
    first_name: str
    last_name: str
    email: Optional[str]
    phone_number: Optional[str]
    role: Optional[str]

class ClientUserCreate(ClientUserBase):
    client_id: UUID4
    hashed_password: str

class ClientUserOut(ClientUserBase):
    id: UUID4
    client_id: UUID4
    class Config:
        from_attributes = True



# ------------------- Base -------------------
class ProjectBase(BaseModel):
    title: str
    description: str
    client_id: UUID4

# ------------------- Create -------------------
class ProjectCreate(BaseModel):
    title: str
    description: str | None
    client_id: UUID4
    category_ids: list[UUID4] = []
    thematic_areas: list[ProjectThematicAreaCreate] = []  
    collaborator_ids: list[UUID4] = []
    media_source_ids: list[UUID4] = []
    report_avenue_ids: list[UUID4] = []
    report_time_ids: list[UUID4] = []
    report_consultation_ids: list[UUID4] = []

# ------------------- Update -------------------
class ProjectUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category_ids: Optional[List[UUID4]] = None
    thematic_area_ids: Optional[List[UUID4]] = None
    collaborator_ids: Optional[List[UUID4]] = None
    media_source_ids: Optional[List[UUID4]] = None
    report_avenue_ids: Optional[List[UUID4]] = None
    report_time_ids: Optional[List[UUID4]] = None
    report_consultation_ids: Optional[List[UUID4]] = None

# ------------------- Output -------------------
class ProjectOut(ProjectBase):
    id: UUID4
    categories: List["ProjectCategoryOut"] = []
    thematic_areas: List["ProjectThematicAreaOut"] = []
    collaborators: List["ClientUserOut"] = []
    media_sources: List["MediaSourceOut"] = []
    report_avenues: List["ReportAvenueOut"] = []
    report_times: List["ReportTimeOut"] = []
    report_consultations: List["ReportConsultationOut"] = []

    class Config:
        from_attributes = True


class ProjectFilters(BaseModel):
    title: Optional[str] = None
    client_id: Optional[uuid.UUID] = None
    status: Optional[ProjectStatus] = None
    sort: Optional[str] = "desc"  # asc | desc




# -----------------------------------
# Get Project Details Needed for ML
# -----------------------------------
class ProjectMLDetailsOut(BaseModel):
    id: UUID4
    title: str
    thematic_areas: List[str]
    media_sources: List[str]




# -----------------------------------
# Project ML Details Create/Update
# -----------------------------------
class ProjectMLDetailsCreateUpdate(BaseModel):
    project_id: Optional[UUID4] = None
    project_title: Optional[str] = None






class MLCSVRequest(BaseModel):
    project_id: UUID4
    csv_url: str


class MLCSVStoredResponse(BaseModel):
    project_id: UUID4
    total_rows: int
    status: str = "stored"
