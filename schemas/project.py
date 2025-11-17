from pydantic import BaseModel, UUID4, Field
from typing import List, Optional

class ProjectCategoryBase(BaseModel):
    category: str

class ProjectCategoryCreate(ProjectCategoryBase):
    pass

class ProjectCategoryOut(ProjectCategoryBase):
    id: UUID4
    class Config:
        from_attributes = True


class ProjectThematicAreaBase(BaseModel):
    area: str
    title: Optional[str] = None
    description: Optional[str] = None
    monitoring_objective: Optional[str] = None

class ProjectThematicAreaCreate(ProjectThematicAreaBase):
    pass

class ProjectThematicAreaOut(ProjectThematicAreaBase):
    id: UUID4
    class Config:
        from_attributes = True



class MediaCategoryBase(BaseModel):
    name: str

class MediaCategoryOut(MediaCategoryBase):
    id: UUID4
    media_sources: List["MediaSourceOut"] = []
    class Config:
        from_attributes = True


class MediaSourceBase(BaseModel):
    name: str
    category_id: UUID4

class MediaSourceOut(MediaSourceBase):
    id: UUID4
    class Config:
        from_attributes = True



class ReportAvenueBase(BaseModel):
    name: str

class ReportAvenueOut(ReportAvenueBase):
    id: UUID4
    class Config:
        from_attributes = True

class ReportTimeBase(BaseModel):
    name: str

class ReportTimeOut(ReportTimeBase):
    id: UUID4
    class Config:
        from_attributes = True

class ReportConsultationBase(BaseModel):
    name: str

class ReportConsultationOut(ReportConsultationBase):
    id: UUID4
    class Config:
        from_attributes = True



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
    thematic_areas: list[ProjectThematicAreaCreate] = []  # Allow creating new thematic areas
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




# -----------------------------------
# Get Project Details Needed for ML
# -----------------------------------
class ProjectMLDetailsOut(BaseModel):
    id: UUID4
    title: str
    thematic_areas: List[str] = []

    class Config:
        from_attributes = True