import uuid
from sqlalchemy import UUID, Boolean, DateTime, Enum, String, Table, Column, ForeignKey, func
from sqlalchemy.orm import relationship
from models.base import Base
from models.enums import ProjectStatus
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.dialects.postgresql import JSONB


# Junction tables
project_category = Table(
    "project_category",
    Base.metadata,
    Column("project_id", ForeignKey("projects.id"), primary_key=True),
    Column("project_category_id", ForeignKey("project_categories.id"), primary_key=True)
)

project_thematic_area = Table(
    "project_thematic_area",
    Base.metadata,
    Column("project_id", ForeignKey("projects.id"), primary_key=True),
    Column("project_thematic_area_id", ForeignKey("project_thematic_areas.id"), primary_key=True)
)


project_collaborators = Table(
    "project_collaborators",
    Base.metadata,
    Column("project_id", ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True),
    Column("collaborator_id", ForeignKey("client_users.id", ondelete="CASCADE"), primary_key=True)
)

# ---------------- Junction Tables ----------------

project_report_avenues = Table(
    "project_report_avenues",
    Base.metadata,
    Column("project_id", ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True),
    Column("report_avenue_id", ForeignKey("report_avenues.id", ondelete="CASCADE"), primary_key=True)
)

project_report_times = Table(
    "project_report_times",
    Base.metadata,
    Column("project_id", ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True),
    Column("report_time_id", ForeignKey("report_times.id", ondelete="CASCADE"), primary_key=True)
)

project_report_consultations = Table(
    "project_report_consultations",
    Base.metadata,
    Column("project_id", ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True),
    Column("report_consultation_id", ForeignKey("report_consultations.id", ondelete="CASCADE"), primary_key=True)
)

# project_media_sources = Table(
#     "project_media_sources",
#     Base.metadata,
#     Column("project_id", ForeignKey("projects.id"), primary_key=True),
#     Column("media_source_id", ForeignKey("media_sources.id"), primary_key=True) 
# )


# ---------------- Project ----------------
class Project(Base):
    __tablename__ = "projects"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(50), nullable=False, index=True)
    description = Column(String(500), nullable=False)
    client_id = Column(UUID(as_uuid=True), ForeignKey("client.id", ondelete="CASCADE"), nullable=False)
    status = Column(Enum(ProjectStatus), default=ProjectStatus.draft, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    is_deleted = Column(Boolean, default=False)   

    # Relationship to Client
    client = relationship("Client", back_populates="projects")
    
    #
    ml_results = relationship("MLAnalysisResult", back_populates="project", cascade="all, delete")


    # Many-to-many: Project <-> Category
    categories = relationship(
        "ProjectCategory",
        secondary=project_category,
        back_populates="projects"
    )

    # Many-to-many: Project <-> Thematic Areas
    thematic_areas = relationship(
        "ProjectThematicAreas",
        secondary=project_thematic_area,
        back_populates="projects"
    )

    # One-to-many: Project <-> ProjectMediaSources (junction for MediaSource)
    media_sources_link = relationship(
        "ProjectMediaSources",
        back_populates="project",
        cascade="all, delete-orphan"
    )

    media_sources = association_proxy("media_sources_link", "media_source")

    collaborators = relationship(
        "ClientUser",
        secondary=project_collaborators,
        back_populates="projects"
    )


    report_avenues = relationship(
        "ReportAvenue",
        secondary=project_report_avenues,
        back_populates="projects"
    )

    report_times = relationship(
        "ReportTime",
        secondary=project_report_times,
        back_populates="projects"
    )

    report_consultations = relationship(
        "ReportConsultation",
        secondary=project_report_consultations,
        back_populates="projects"
    )



# ---------------- Thematic Areas ----------------
class ProjectThematicAreas(Base):
    __tablename__ = "project_thematic_areas"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    area = Column(String, nullable=False)
    title = Column(String, nullable=False)
    description = Column(String, nullable=True)
    monitoring_objective = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    is_deleted = Column(Boolean, default=False)

    projects = relationship(
        "Project",
        secondary=project_thematic_area,
        back_populates="thematic_areas"
    )


# ---------------- Categories ----------------
class ProjectCategory(Base):
    __tablename__ = "project_categories"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    category = Column(String, nullable=False)
    description= Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    is_deleted = Column(Boolean, default=False)

    projects = relationship(
        "Project",
        secondary=project_category,
        back_populates="categories"
    )


# ---------------- Media Category ----------------
class MediaCategory(Base):
    __tablename__ = "media_categories"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    description= Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    is_deleted = Column(Boolean, default=False)

    media_sources = relationship("MediaSource", back_populates="category")


# ---------------- Media Source ----------------
class MediaSource(Base):
    __tablename__ = "media_sources"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    category_id = Column(UUID(as_uuid=True), ForeignKey("media_categories.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    is_deleted = Column(Boolean, default=False)

    category = relationship("MediaCategory", back_populates="media_sources")
    projects = relationship("ProjectMediaSources", back_populates="media_source")


# ---------------- Junction: Project ↔ MediaSource ----------------
class ProjectMediaSources(Base):
    __tablename__ = "project_media_sources"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    media_source_id = Column(UUID(as_uuid=True), ForeignKey("media_sources.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    is_deleted = Column(Boolean, default=False)

    project = relationship("Project", back_populates="media_sources_link")
    media_source = relationship("MediaSource", back_populates="projects")



# ------------------- Report Avenues -------------------
class ReportAvenue(Base):
    __tablename__ = "report_avenues"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, unique=True, nullable=False)  # e.g., 'web', 'email', 'mobile'
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    is_deleted = Column(Boolean, default=False)

    projects = relationship(
        "Project",
        secondary="project_report_avenues",
        back_populates="report_avenues"
    )


# ------------------- Report Times -------------------
class ReportTime(Base):
    __tablename__ = "report_times"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, unique=True, nullable=False)  # e.g., 'daily', 'monthly', 'yearly'
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    is_deleted = Column(Boolean, default=False)

    projects = relationship(
        "Project",
        secondary="project_report_times",
        back_populates="report_times"
    )


# ------------------- Report Consultations -------------------
class ReportConsultation(Base):
    __tablename__ = "report_consultations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, unique=True, nullable=False)  # e.g., 'on-demand', 'scheduled', etc.
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    is_deleted = Column(Boolean, default=False)

    projects = relationship(
        "Project",
        secondary="project_report_consultations",
        back_populates="report_consultations"
    )
