import uuid
from pydantic import BaseModel, UUID4, Field
from typing import List, Optional

from models.enums import ProjectMediaCategory, ProjectStatus
from models.project import MediaSource, Project, ProjectThematicAreas

class ProjectCategoryBase(BaseModel):
    name: str
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
    name: Optional[str] = None
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
    description: Optional[str] = None

class MediaCategoryOut(MediaCategoryBase):
    id: UUID4
    # media_sources: List["MediaSourceOut"] = []
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
    category_name: ProjectMediaCategory

class MediaSourceOut(BaseModel):
    id: UUID4
    name: str
    category_name: ProjectMediaCategory   # <-- return readable enum value

    class Config:
        from_attributes = True


class MediaSourceFilters(BaseModel):
    search: Optional[str] = None
    category_id: Optional[uuid.UUID] = None
    sort_by: Optional[str] = "created_at"
    sort_order: Optional[str] = "desc"


class MediaSourceUpdate(BaseModel):
    name: Optional[str] = None
    category_name: Optional[ProjectMediaCategory] = None











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
    categories: List[ProjectCategoryOut] = []
    thematic_areas: List[ProjectThematicAreaOut] = []
    collaborators: List[ClientUserOut] = []
    media_sources: List[MediaSourceOut] = []
    report_avenues: List[ReportAvenueOut] = []
    report_times: List[ReportTimeOut] = []
    report_consultations: List[ReportConsultationOut] = []

    @classmethod
    def model_validate(cls, model):
        return cls(
            id=model.id,
            title=model.title,
            description=model.description,
            client_id=model.client_id,
            categories=[
                ProjectCategoryOut.model_validate(c)
                for c in model.categories
            ],
            thematic_areas=[
                ProjectThematicAreaOut.model_validate(t)
                for t in model.thematic_areas
            ],
            collaborators=[
                ClientUserOut.model_validate(u)
                for u in model.collaborators
            ],
            media_sources=[
                MediaSourceOut.model_validate(ms)
                for ms in model.media_sources
            ],
            report_avenues=[
                ReportAvenueOut.model_validate(a)
                for a in model.report_avenues
            ],
            report_times=[
                ReportTimeOut.model_validate(t)
                for t in model.report_times
            ],
            report_consultations=[
                ReportConsultationOut.model_validate(c)
                for c in model.report_consultations
            ]
        )



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



































# ============================================================
# NEW SAFE SERIALIZATION SCHEMAS (ONLY FOR PROJECT OUTPUT)
# ============================================================

# from pydantic import BaseModel, UUID4
# from typing import List, Optional
# from models.enums import ProjectMediaCategory
# from models.project import MediaSource, ProjectThematicAreas


# -------------------------------
# SAFE Thematic Area Output
# -------------------------------
class ProjectThematicAreaOutSafe(BaseModel):
    id: UUID4
    area: str
    title: str
    description: Optional[str] = None
    monitoring_objectives: List[str]

    @classmethod
    def from_model(cls, model: ProjectThematicAreas):
        return cls(
            id=model.id,
            area=model.area,
            title=model.title,
            description=model.description,
            monitoring_objectives=model.monitoring_objective or []
        )


# -------------------------------
# SAFE Media Source Output
# -------------------------------
class MediaSourceOutSafe(BaseModel):
    id: UUID4
    name: str
    category_name: ProjectMediaCategory

    @classmethod
    def from_model(cls, model: MediaSource):
        # model.category.name is the DB string, convert to enum
        clean = ProjectMediaCategory(model.category.name)
        return cls(
            id=model.id,
            name=model.name,
            category_name=clean
        )


# -------------------------------
# SAFE Project Out
# -------------------------------
class ProjectOutSafe(BaseModel):
    id: UUID4
    title: str
    description: str
    client_id: UUID4

    categories: List[ProjectCategoryOut] = []
    thematic_areas: List[ProjectThematicAreaOutSafe] = []
    collaborators: List[ClientUserOut] = []
    media_sources: List[MediaSourceOutSafe] = []
    report_avenues: List[ReportAvenueOut] = []
    report_times: List[ReportTimeOut] = []
    report_consultations: List[ReportConsultationOut] = []

    @classmethod
    def from_model(cls, model):
        return cls(
            id=model.id,
            title=model.title,
            description=model.description,
            client_id=model.client_id,

            categories=[
                ProjectCategoryOut.model_validate(c)
                for c in model.categories
            ],

            thematic_areas=[
                ProjectThematicAreaOutSafe.from_model(t)
                for t in model.thematic_areas
            ],

            collaborators=[
                ClientUserOut.model_validate(u)
                for u in model.collaborators
            ],

            media_sources=[
                MediaSourceOutSafe.from_model(ms)
                for ms in model.media_sources
            ],

            report_avenues=[
                ReportAvenueOut.model_validate(a)
                for a in model.report_avenues
            ],

            report_times=[
                ReportTimeOut.model_validate(t)
                for t in model.report_times
            ],

            report_consultations=[
                ReportConsultationOut.model_validate(c)
                for c in model.report_consultations
            ]
        )














# -----------------------------
# Safe Media Source Output
# -----------------------------
class MediaSourceOutSafe(BaseModel):
    id: UUID4
    name: str
    category_name: ProjectMediaCategory

    @staticmethod
    def from_model(ms):
        return MediaSourceOutSafe(
            id=ms.id,
            name=ms.name,
            category_name=ProjectMediaCategory(ms.category.name)
        )


# -----------------------------
# Safe Thematic Area Output
# -----------------------------
class ProjectThematicAreaOutSafe(BaseModel):
    id: UUID4
    area: str
    title: str
    description: str | None
    monitoring_objectives: List[str]

    @staticmethod
    def from_model(ta):
        return ProjectThematicAreaOutSafe(
            id=ta.id,
            area=ta.area,
            title=ta.title,
            description=ta.description,
            monitoring_objectives=ta.monitoring_objective or []
        )


# -----------------------------
# Safe Project Output
# -----------------------------
class ProjectOutSafe(BaseModel):
    id: UUID4
    title: str
    description: str
    client_id: UUID4

    categories: List[ProjectCategoryOut]
    collaborators: List[ClientUserOut]
    media_sources: List[MediaSourceOutSafe]
    thematic_areas: List[ProjectThematicAreaOutSafe]

    report_avenues: List[ReportAvenueOut]
    report_times: List[ReportTimeOut]
    report_consultations: List[ReportConsultationOut]

    @staticmethod
    def from_model(project: Project):

        return ProjectOutSafe(
            id=project.id,
            title=project.title,
            description=project.description,
            client_id=project.client_id,

            categories=[
                ProjectCategoryOut.model_validate(c)
                for c in project.categories
            ],

            collaborators=[
                ClientUserOut.model_validate(c)
                for c in project.collaborators
            ],

            thematic_areas=[
                ProjectThematicAreaOutSafe.from_model(t)
                for t in project.thematic_areas
            ],

            media_sources=[
                MediaSourceOutSafe.from_model(ms)
                for ms in project.media_sources
            ],

            report_avenues=[
                ReportAvenueOut.model_validate(r)
                for r in project.report_avenues
            ],

            report_times=[
                ReportTimeOut.model_validate(t)
                for t in project.report_times
            ],

            report_consultations=[
                ReportConsultationOut.model_validate(c)
                for c in project.report_consultations
            ],
        )
