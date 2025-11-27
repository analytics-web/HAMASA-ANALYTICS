from sqlalchemy import (
    Column, String, Text, DateTime, Enum, ForeignKey, Integer
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime

from models.base import Base
# from models.enums import MediaFormatEnum  # Optional: define if you want
                                          # otherwise use String
                                          
class ProjectReport(Base):
    __tablename__ = "project_report"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Link to project
    project_id = Column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False
    )

    # =============== Fields from your sample data ===============

    # "2025-11-26 01:35:19"
    publication_date = Column(DateTime, nullable=False)

    # "Kwanini Rais Samia anatupiwa lawama?"
    title = Column(String(500), nullable=False)

    # Long text content
    content = Column(Text, nullable=True)

    # "BBC"
    source = Column(String(255), nullable=True)

    # media_category: "" (empty), so optional
    media_category = Column(String(255), nullable=True)

    # "article"
    media_format = Column(String(50), nullable=True)

    # "AI FOUND NO MATCH"
    thematic_area = Column(String(255), nullable=True)

    # "AI did not classify this article..."
    thematic_description = Column(Text, nullable=True)

    # objectives: [] → JSONB is ideal here
    objectives = Column(JSONB, nullable=True)

    # link to the source
    link = Column(Text, nullable=True)

    # Status: "Unverified"
    status = Column(String(50), nullable=True)

    # =============== Your requested flexible column ===============
    extra_metadata = Column(JSONB, default=dict)

    # =============== Optional timestamps ===============
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

    # Relationship (if you want to access report.project)
    project = relationship("Project", back_populates="reports")
